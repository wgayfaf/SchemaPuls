"""接口探针层 CRUD、即时业务校验 (test-run)、时序指标与历史流水"""
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy import text

from app.database import get_session
from app.models import (
    Environment, ServiceGroup, MachineNode, ApiProbe,
    ApiProbeHistory, MonitorTarget,
)
from app.schemas.api_probe import (
    ApiPayload, ApiTestRunPayload,
    BatchApiIdsPayload, BatchToggleActivePayload, BatchSetIntervalPayload
)
from app.services.probe_service import execute_api_probe, check_schema
from app.services.scheduler import add_api_job, remove_api_job, add_target_job, remove_target_job

router = APIRouter(prefix="/api/apis", tags=["apis"])


@router.get("")
def list_apis(
    machine_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    stmt = select(ApiProbe)
    if machine_id:
        stmt = stmt.where(ApiProbe.machine_id == machine_id)
    apis = session.exec(stmt).all()

    result = []
    for a in apis:
        m = session.get(MachineNode, a.machine_id)
        grp = session.get(ServiceGroup, m.group_id) if m and m.group_id else None
        env = session.get(Environment, grp.environment_id) if grp else None

        if environment_id and (not env or env.id != environment_id):
            continue

        host = m.host if m else "127.0.0.1"
        port = m.port if m else 80
        scheme = "https" if port == 443 else "http"
        port_str = f":{port}" if port not in [80, 443] else ""
        path = a.http_path if a.http_path.startswith("/") else f"/{a.http_path}"
        effective_base = a.base_url or (m.base_url if m else None)
        if effective_base and effective_base.strip():
            full_url = f"{effective_base.strip().rstrip('/')}{path}"
        else:
            full_url = f"{scheme}://{host}{port_str}{path}"

        result.append({
            "id": a.id,
            "machine_id": a.machine_id,
            "name": a.name,
            "base_url": a.base_url,
            "http_path": a.http_path,
            "http_method": a.http_method,
            "http_params": a.http_params or [],
            "http_headers": a.http_headers or {},
            "http_body_type": a.http_body_type or "none",
            "http_body": a.http_body,
            "auth_type": a.auth_type or "none",
            "auth_config": a.auth_config or {},
            "expected_schema": a.expected_schema,
            "schema_configured": bool(a.expected_schema),
            "pre_actions": a.pre_actions or [],
            "post_actions": a.post_actions or [],
            "cron_interval_minutes": a.cron_interval_minutes,
            "is_active": a.is_active,
            "retry_threshold": a.retry_threshold,
            "silence_minutes": a.silence_minutes,
            "email_receivers": a.email_receivers or [],
            "current_status": a.current_status,
            "consecutive_failures": a.consecutive_failures,
            "last_http_code": a.last_http_code,
            "last_http_latency_ms": a.last_http_latency_ms,
            "last_schema_matched": a.last_schema_matched,
            "last_probed_at": a.last_probed_at.isoformat() if a.last_probed_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "machine_name": m.name if m else f"node-{host}:{port}",
            "machine_host": host,
            "machine_port": port,
            "machine_status": m.current_status if m else "UNKNOWN",
            "environment_id": env.id if env else None,
            "environment_name": env.name if env else "默认环境",
            "group_name": grp.name if grp else "核心集群",
            "full_url": full_url
        })
    return result


@router.post("/test-run")
async def test_run_api(data: ApiTestRunPayload, session: Session = Depends(get_session)):
    """即时在线调试运行探针 (Postman 风格即时发包与响应比对)"""
    machine = session.get(MachineNode, data.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Associated MachineNode not found")

    # 关联宿主机器的环境与环境变量
    grp = session.get(ServiceGroup, machine.group_id) if machine.group_id else None
    env = session.get(Environment, grp.environment_id) if grp and grp.environment_id else None
    env_vars = dict(env.variables or {}) if env and env.variables else {}

    auth_token = None
    if data.auth_type == "bearer":
        auth_token = data.auth_config.get("token")

    from app.services.template_engine import (
        parse_params_to_dict, parse_headers_to_dict, render_macro_string, resolve_path_variables
    )

    req_headers = parse_headers_to_dict(data.http_headers, auth_token=auth_token)
    if data.auth_type == "bearer" and auth_token:
        if "authorization" not in [k.lower() for k in req_headers]:
            req_headers["Authorization"] = f"Bearer {auth_token}"
    elif data.auth_type == "basic":
        u = data.auth_config.get("username", "")
        p = data.auth_config.get("password", "")
        if u or p:
            import base64
            b64_val = base64.b64encode(f"{u}:{p}".encode()).decode()
            if "authorization" not in [k.lower() for k in req_headers]:
                req_headers["Authorization"] = f"Basic {b64_val}"
    elif data.auth_type == "custom_header":
        hk = (data.auth_config or {}).get("header_key", "").strip()
        hv = (data.auth_config or {}).get("header_value", "")
        if hk and hk.lower() not in [k.lower() for k in req_headers]:
            req_headers[hk] = hv

    raw_params = parse_params_to_dict(data.http_params, auth_token=auth_token)
    rendered_body = render_macro_string(data.http_body, auth_token=auth_token) if data.http_body else None

    rendered_path = render_macro_string(data.http_path, auth_token=auth_token)
    if not rendered_path.startswith("/"):
        rendered_path = "/" + rendered_path

    # 解析并替换路径参数 (如 /detail/{tableId} 或 /detail/:tableId)
    # 将已被替换进路径的参数从 req_params 中剔除，防止被拼接成查询字符串
    rendered_path, req_params = resolve_path_variables(rendered_path, raw_params, env_vars)

    # 执行【前置操作 (Pre-request Actions)】
    from app.services.action_engine import execute_pre_actions, execute_post_actions
    final_headers, final_params, final_body, final_path, variables, pre_updated_env = execute_pre_actions(
        pre_actions=data.pre_actions,
        headers=req_headers,
        params=req_params,
        body=rendered_body,
        path=rendered_path,
        auth_token=auth_token,
        environment_variables=env_vars
    )

    # 前置操作若动态生成了变量或修改了参数，进行二次路径变量安全兜底解析
    final_path, final_params = resolve_path_variables(final_path, final_params, variables)

    if not final_path.startswith("/"):
        final_path = "/" + final_path

    effective_base = data.base_url or (machine.base_url if machine else None)
    if effective_base and effective_base.strip():
        url = f"{effective_base.strip().rstrip('/')}{final_path}"
    else:
        scheme = "https" if machine.port == 443 else "http"
        url = (
            f"{scheme}://{machine.host}:{machine.port}{final_path}"
            if machine.port not in [80, 443]
            else f"{scheme}://{machine.host}{final_path}"
        )

    from app.services.probe_service import check_http_detailed
    http_ok, http_code, http_ms, json_data, http_err, resp_headers, resp_text = await check_http_detailed(
        url,
        method=data.http_method,
        headers=final_headers,
        params=final_params if final_params else None,
        body=final_body,
        body_type=data.http_body_type
    )

    schema_matched = None
    schema_errors = []
    schema_configured = bool(data.expected_schema)
    if data.expected_schema and isinstance(data.expected_schema, dict):
        if json_data is not None:
            schema_matched, schema_errors = check_schema(json_data, data.expected_schema)
        else:
            schema_matched = False
            schema_errors = [{"field": "$root", "validator": "empty", "message": http_err or "未收到有效 JSON 响应"}]

    # 执行【后置操作 (Post-response Actions / Assertions)】
    all_assertions_passed, assertions_result, extracted_vars, post_updated_env = execute_post_actions(
        post_actions=data.post_actions,
        status_code=http_code,
        latency_ms=http_ms,
        response_headers=resp_headers,
        response_data=json_data,
        response_text=resp_text,
        context_variables=variables,
        environment_variables=env_vars
    )

    # 同步环境变量更新并持久化到数据库
    all_updated_env = {}
    all_updated_env.update(pre_updated_env)
    all_updated_env.update(post_updated_env)
    if all_updated_env and env:
        from sqlalchemy.orm.attributes import flag_modified
        current_vars = dict(env.variables or {})
        current_vars.update(all_updated_env)
        env.variables = current_vars
        flag_modified(env, "variables")
        session.add(env)
        session.commit()
        session.refresh(env)
        env_vars = current_vars

    return {
        "status_code": http_code,
        "latency_ms": http_ms,
        "is_ok": http_ok,
        "error_message": http_err,
        "response_data": json_data,
        "response_headers": resp_headers,
        "response_text": resp_text[:1000] if resp_text else None,
        "schema_matched": schema_matched,
        "schema_configured": schema_configured,
        "schema_errors": schema_errors,
        "assertions_summary": {
            "all_passed": all_assertions_passed,
            "total": len(assertions_result),
            "passed_count": sum(1 for a in assertions_result if a.get("passed", False))
        },
        "assertions_result": assertions_result,
        "extracted_variables": extracted_vars,
        "environment": {
            "id": env.id if env else None,
            "name": env.name if env else "默认环境",
            "variables": env_vars,
            "updated_variables": all_updated_env
        },
        "request_url": url,
        "resolved_url": url,
        "rendered_headers": final_headers,
        "rendered_params": final_params,
        "rendered_body": final_body,
        "script_error": variables.get("_script_error"),
        "console_logs": variables.get("_console_logs", [])
    }


@router.post("")
def create_api(data: ApiPayload, session: Session = Depends(get_session)):
    machine = session.get(MachineNode, data.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Associated MachineNode not found")

    api = ApiProbe(
        machine_id=data.machine_id,
        name=data.name,
        base_url=data.base_url,
        http_path=data.http_path,
        http_method=data.http_method,
        http_params=data.http_params,
        http_headers=data.http_headers,
        http_body_type=data.http_body_type,
        http_body=data.http_body,
        auth_type=data.auth_type,
        auth_config=data.auth_config,
        expected_schema=data.expected_schema,
        pre_actions=data.pre_actions,
        post_actions=data.post_actions,
        cron_interval_minutes=data.cron_interval_minutes,
        is_active=data.is_active,
        retry_threshold=data.retry_threshold,
        silence_minutes=data.silence_minutes,
        email_receivers=data.email_receivers
    )
    session.add(api)
    session.commit()
    session.refresh(api)

    # 防御性清理该接口 ID 可能残留的历史脏数据（如旧测试用例或删除残留），确保新接口历史 100% 纯净专属
    session.exec(text(f"DELETE FROM api_probe_histories WHERE api_probe_id = {api.id}"))
    session.commit()

    add_api_job(api)

    grp = session.get(ServiceGroup, machine.group_id) if machine.group_id else None
    env = session.get(Environment, grp.environment_id) if grp else None

    # 同步维护 MonitorTarget 以保障大盘与兼容平铺视图
    target = MonitorTarget(
        name=api.name,
        group_name=env.name if env else "生产环境",
        host=machine.host,
        port=machine.port,
        http_path=api.http_path,
        http_method=api.http_method,
        cron_interval_minutes=api.cron_interval_minutes,
        expected_schema=api.expected_schema,
        email_receivers=api.email_receivers,
        retry_threshold=api.retry_threshold,
        silence_minutes=api.silence_minutes
    )
    session.add(target)
    session.commit()
    session.refresh(target)
    add_target_job(target)

    scheme = "https" if machine.port == 443 else "http"
    port_str = f":{machine.port}" if machine.port not in [80, 443] else ""
    path = api.http_path if api.http_path.startswith("/") else f"/{api.http_path}"
    if api.base_url and api.base_url.strip():
        full_url = f"{api.base_url.strip().rstrip('/')}{path}"
    else:
        full_url = f"{scheme}://{machine.host}{port_str}{path}"

    return {
        "id": api.id,
        "machine_id": api.machine_id,
        "name": api.name,
        "base_url": api.base_url,
        "http_path": api.http_path,
        "http_method": api.http_method,
        "http_params": api.http_params or [],
        "http_headers": api.http_headers or {},
        "http_body_type": api.http_body_type or "none",
        "http_body": api.http_body,
        "auth_type": api.auth_type or "none",
        "auth_config": api.auth_config or {},
        "expected_schema": api.expected_schema,
        "pre_actions": api.pre_actions or [],
        "post_actions": api.post_actions or [],
        "cron_interval_minutes": api.cron_interval_minutes,
        "is_active": api.is_active,
        "current_status": api.current_status,
        "machine_name": machine.name,
        "machine_host": machine.host,
        "machine_port": machine.port,
        "environment_id": env.id if env else None,
        "environment_name": env.name if env else "默认环境",
        "full_url": full_url
    }


@router.put("/{id}")
def update_api(id: int, data: ApiPayload, session: Session = Depends(get_session)):
    api = session.get(ApiProbe, id)
    if not api:
        raise HTTPException(status_code=404, detail="ApiProbe not found")

    machine = session.get(MachineNode, data.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Associated MachineNode not found")

    old_name = api.name
    api.machine_id = data.machine_id
    api.name = data.name
    api.base_url = data.base_url
    api.http_path = data.http_path
    api.http_method = data.http_method
    api.http_params = data.http_params
    api.http_headers = data.http_headers
    api.http_body_type = data.http_body_type
    api.http_body = data.http_body
    api.auth_type = data.auth_type
    api.auth_config = data.auth_config
    api.expected_schema = data.expected_schema
    api.pre_actions = data.pre_actions
    api.post_actions = data.post_actions
    api.cron_interval_minutes = data.cron_interval_minutes
    api.is_active = data.is_active
    api.email_receivers = data.email_receivers
    session.add(api)
    session.commit()
    session.refresh(api)
    add_api_job(api)

    # 同步更新对应 MonitorTarget (若匹配)
    targets = session.exec(select(MonitorTarget).where(MonitorTarget.name == old_name)).all()
    for t in targets:
        t.name = api.name
        t.host = machine.host
        t.port = machine.port
        t.http_path = api.http_path
        t.http_method = api.http_method
        t.expected_schema = api.expected_schema
        t.cron_interval_minutes = api.cron_interval_minutes
        t.email_receivers = api.email_receivers
        session.add(t)
        add_target_job(t)
    session.commit()

    grp = session.get(ServiceGroup, machine.group_id) if machine.group_id else None
    env = session.get(Environment, grp.environment_id) if grp else None
    scheme = "https" if machine.port == 443 else "http"
    port_str = f":{machine.port}" if machine.port not in [80, 443] else ""
    path = api.http_path if api.http_path.startswith("/") else f"/{api.http_path}"
    if api.base_url and api.base_url.strip():
        full_url = f"{api.base_url.strip().rstrip('/')}{path}"
    else:
        full_url = f"{scheme}://{machine.host}{port_str}{path}"

    return {
        "id": api.id,
        "machine_id": api.machine_id,
        "name": api.name,
        "base_url": api.base_url,
        "http_path": api.http_path,
        "http_method": api.http_method,
        "http_params": api.http_params or [],
        "http_headers": api.http_headers or {},
        "http_body_type": api.http_body_type or "none",
        "http_body": api.http_body,
        "auth_type": api.auth_type or "none",
        "auth_config": api.auth_config or {},
        "expected_schema": api.expected_schema,
        "pre_actions": api.pre_actions or [],
        "post_actions": api.post_actions or [],
        "cron_interval_minutes": api.cron_interval_minutes,
        "is_active": api.is_active,
        "current_status": api.current_status,
        "machine_name": machine.name,
        "machine_host": machine.host,
        "machine_port": machine.port,
        "environment_id": env.id if env else None,
        "environment_name": env.name if env else "默认环境",
        "full_url": full_url
    }


@router.post("/{id}/toggle-active")
def toggle_api_active(id: int, session: Session = Depends(get_session)):
    """快捷切换接口探针的自动定时探测开关"""
    api = session.get(ApiProbe, id)
    if not api:
        raise HTTPException(status_code=404, detail="接口探针不存在")
    api.is_active = not api.is_active
    session.add(api)
    session.commit()
    session.refresh(api)
    add_api_job(api)

    # 同步对应的兼容 MonitorTarget
    targets = session.exec(select(MonitorTarget).where(MonitorTarget.name == api.name)).all()
    for t in targets:
        t.is_active = api.is_active
        session.add(t)
        add_target_job(t)
    session.commit()

    return {
        "status": "ok",
        "id": api.id,
        "name": api.name,
        "is_active": api.is_active,
        "cron_interval_minutes": api.cron_interval_minutes
    }


@router.delete("/{id}")
def delete_api(id: int, session: Session = Depends(get_session)):
    api = session.get(ApiProbe, id)
    if not api:
        raise HTTPException(status_code=404, detail="ApiProbe not found")
    name = api.name
    remove_api_job(id)
    # 级联清除该接口专属历史探测流水，杜绝孤儿脏数据污染
    session.exec(text(f"DELETE FROM api_probe_histories WHERE api_probe_id = {id}"))
    targets = session.exec(select(MonitorTarget).where(MonitorTarget.name == name)).all()
    for t in targets:
        remove_target_job(t.id)
        session.exec(text(f"DELETE FROM probe_histories WHERE target_id = {t.id}"))
        session.delete(t)
    session.delete(api)
    session.commit()
    return {"status": "ok", "message": f"接口探针 id={id} 已删除"}


@router.post("/batch-delete")
def batch_delete_apis(data: BatchApiIdsPayload, session: Session = Depends(get_session)):
    """批量删除选中的接口探针"""
    if not data.ids:
        return {"status": "ok", "deleted_count": 0, "message": "未传入任何接口ID"}

    deleted_count = 0
    for api_id in data.ids:
        api = session.get(ApiProbe, api_id)
        if not api:
            continue
        name = api.name
        remove_api_job(api_id)
        session.exec(text(f"DELETE FROM api_probe_histories WHERE api_probe_id = {api_id}"))
        targets = session.exec(select(MonitorTarget).where(MonitorTarget.name == name)).all()
        for t in targets:
            remove_target_job(t.id)
            session.exec(text(f"DELETE FROM probe_histories WHERE target_id = {t.id}"))
            session.delete(t)
        session.delete(api)
        deleted_count += 1

    session.commit()
    return {"status": "ok", "deleted_count": deleted_count, "message": f"成功批量删除 {deleted_count} 个接口探针"}


@router.post("/batch-toggle-active")
def batch_toggle_api_active(data: BatchToggleActivePayload, session: Session = Depends(get_session)):
    """批量启用/关闭选中的接口探针的自动探测周期"""
    if not data.ids:
        return {"status": "ok", "updated_count": 0, "message": "未传入任何接口ID"}

    updated_count = 0
    for api_id in data.ids:
        api = session.get(ApiProbe, api_id)
        if not api:
            continue
        if data.is_active is not None:
            api.is_active = data.is_active
        else:
            api.is_active = not api.is_active
        session.add(api)
        add_api_job(api)

        # 同步对应的兼容 MonitorTarget
        targets = session.exec(select(MonitorTarget).where(MonitorTarget.name == api.name)).all()
        for t in targets:
            t.is_active = api.is_active
            session.add(t)
            add_target_job(t)
        updated_count += 1

    session.commit()
    return {
        "status": "ok",
        "updated_count": updated_count,
        "is_active": data.is_active,
        "message": f"成功批量更新 {updated_count} 个接口探针的探测状态"
    }


@router.post("/batch-set-interval")
def batch_set_api_interval(data: BatchSetIntervalPayload, session: Session = Depends(get_session)):
    """批量修改选中的接口探针的探测周期 (分钟)"""
    if not data.ids:
        return {"status": "ok", "updated_count": 0, "message": "未传入任何接口ID"}

    interval = max(1, min(data.cron_interval_minutes, 10080))
    updated_count = 0
    for api_id in data.ids:
        api = session.get(ApiProbe, api_id)
        if not api:
            continue
        api.cron_interval_minutes = interval
        session.add(api)
        if api.is_active:
            add_api_job(api)

        # 同步对应的兼容 MonitorTarget
        targets = session.exec(select(MonitorTarget).where(MonitorTarget.name == api.name)).all()
        for t in targets:
            t.cron_interval_minutes = interval
            session.add(t)
            if t.is_active:
                add_target_job(t)
        updated_count += 1

    session.commit()
    return {
        "status": "ok",
        "updated_count": updated_count,
        "cron_interval_minutes": interval,
        "message": f"成功将 {updated_count} 个接口探针的探测周期修改为 {interval} 分钟"
    }


@router.post("/{id}/trigger")
async def trigger_api_probe(id: int, session: Session = Depends(get_session)):
    """手动立即触发对指定接口的业务状态与 Schema 契约校验 (带熔断守卫)"""
    try:
        history = await execute_api_probe(id)
        api = session.get(ApiProbe, id)
        data = history.model_dump()
        # 附带契约配置状态, 供前端区分"未配置"与"突变" (历史流水列 NOT NULL 统一记录 False)
        data["schema_configured"] = bool(api.expected_schema) if api else False
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{id}/metrics")
def get_api_metrics(id: int, session: Session = Depends(get_session)):
    api = session.get(ApiProbe, id)
    if not api:
        raise HTTPException(status_code=404, detail=f"接口探针 [ID={id}] 不存在")

    machine = session.get(MachineNode, api.machine_id) if api.machine_id else None
    tcp_latency = machine.last_tcp_latency_ms if machine else None

    records = session.exec(
        select(ApiProbeHistory)
        .where(ApiProbeHistory.api_probe_id == id)
        .order_by(ApiProbeHistory.probed_at.desc())
        .limit(100)
    ).all()

    points = [
        {
            "time": r.probed_at.strftime("%H:%M:%S") if r.probed_at else "--:--:--",
            "http_ms": r.http_latency_ms or 0.0,
            "tcp_ms": None if r.circuit_broken else tcp_latency,
            "http_code": r.http_status_code,
            "is_healthy": r.is_healthy,
            "circuit_broken": r.circuit_broken
        }
        for r in reversed(records)
    ]
    return {
        "api_id": id,
        "api_name": api.name,
        "points": points
    }


@router.get("/{id}/history")
def get_api_history(
    id: int,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """接口探针历史探测流水记录 (严格专属当前接口，绝不混入老 targets 或其它接口历史)"""
    api = session.get(ApiProbe, id)
    if not api:
        raise HTTPException(status_code=404, detail=f"接口探针 [ID={id}] 不存在")

    machine = session.get(MachineNode, api.machine_id) if api.machine_id else None
    tcp_ok = (machine.current_status != "OFFLINE") if machine else True
    tcp_latency = machine.last_tcp_latency_ms if machine else None

    # 严格根据 api_probe_id 检索专属历史流水
    records = session.exec(
        select(ApiProbeHistory)
        .where(ApiProbeHistory.api_probe_id == id)
        .order_by(ApiProbeHistory.probed_at.desc())
        .limit(limit)
    ).all()

    res = []
    for r in records:
        res.append({
            "id": r.id,
            "api_probe_id": r.api_probe_id,
            "api_name": api.name,
            "machine_id": r.machine_id,
            "machine_name": machine.name if machine else None,
            "circuit_broken": r.circuit_broken,
            "tcp_ok": False if r.circuit_broken else tcp_ok,
            "tcp_latency_ms": None if r.circuit_broken else tcp_latency,
            "http_status_code": r.http_status_code,
            "http_latency_ms": r.http_latency_ms,
            "schema_matched": r.schema_matched,
            "schema_diff_detail": r.schema_diff_detail,
            "raw_response_snippet": r.raw_response_snippet,
            "is_healthy": r.is_healthy,
            "probed_at": r.probed_at.isoformat() if r.probed_at else None
        })
    return res
