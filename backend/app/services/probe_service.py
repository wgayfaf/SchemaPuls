import asyncio
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import httpx
from jsonschema import Draft7Validator
from sqlmodel import Session, select
from app.models import (
    MachineNode, ApiProbe, MachineProbeHistory, ApiProbeHistory,
    MonitorTarget, ProbeHistory
)
from app.database import engine
from app.services.email_service import (
    send_email_notification,
    generate_alert_email_html,
    generate_recovery_email_html,
    generate_machine_offline_email_html,
    generate_machine_recovery_email_html
)
from app.services.template_engine import (
    render_macro_string,
    render_template_value,
    parse_params_to_dict,
    parse_headers_to_dict
)


# ==========================================================
# 基础探测原子操作
# ==========================================================

async def check_tcp(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, Optional[float], Optional[str]]:
    """TCP Socket 握手连通性与耗时探测"""
    start = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return True, latency_ms, None
    except asyncio.CancelledError:
        raise
    except asyncio.TimeoutError:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return False, latency_ms, f"TCP 连接超时 ({timeout}s)"
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return False, latency_ms, f"TCP 连接失败: {str(e)}"


async def check_http(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    body_type: str = "none",
    timeout: float = 5.0
) -> Tuple[bool, Optional[int], Optional[float], Optional[Dict[str, Any]], Optional[str]]:
    """HTTP 业务请求探测 (支持 Params、Headers、Body 与超时控制)"""
    start = time.perf_counter()
    req_headers = dict(headers or {})
    content = None
    json_body = None

    if body and method.upper() in ["POST", "PUT", "PATCH", "DELETE"]:
        if body_type == "json":
            try:
                json_body = json.loads(body)
                if "content-type" not in [k.lower() for k in req_headers]:
                    req_headers["Content-Type"] = "application/json"
            except Exception:
                content = body.encode("utf-8")
        elif body_type in ["form_data", "raw"]:
            content = body.encode("utf-8")
            if body_type == "form_data" and "content-type" not in [k.lower() for k in req_headers]:
                req_headers["Content-Type"] = "application/x-www-form-urlencoded"

    try:
        async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
            if json_body is not None:
                resp = await client.request(method, url, headers=req_headers, params=params, json=json_body)
            elif content is not None:
                resp = await client.request(method, url, headers=req_headers, params=params, content=content)
            else:
                resp = await client.request(method, url, headers=req_headers, params=params)

            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            try:
                json_data = resp.json()
            except Exception:
                json_data = None
            is_ok = (resp.status_code == 200)
            err = None if is_ok else f"HTTP 状态码异常: {resp.status_code}"
            return is_ok, resp.status_code, latency_ms, json_data, err
    except asyncio.CancelledError:
        raise
    except httpx.TimeoutException:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return False, None, latency_ms, None, f"HTTP 请求超时 ({timeout}s)"
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return False, None, latency_ms, None, f"HTTP 请求异常: {str(e)}"


def check_schema(json_data: Any, expected_schema: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
    """使用 Draft-7 严格比对 JSON 结构"""
    if json_data is None:
        return False, [{"field": "$root", "validator": "type", "message": "响应内容不是合法的 JSON 对象"}]

    validator = Draft7Validator(expected_schema)
    errors = []
    for err in validator.iter_errors(json_data):
        field_path = ".".join([str(p) for p in err.absolute_path]) or "$root"
        err_type = err.validator
        if err_type == "required":
            detail = f"必填字段缺失: {err.message}"
        elif err_type == "type":
            detail = f"字段类型不匹配: {err.message}"
        elif err_type == "additionalProperties":
            detail = f"检测到未声明的新增字段: {err.message}"
        else:
            detail = err.message
        errors.append({"field": field_path, "validator": err_type, "message": detail})

    return (len(errors) == 0), errors


# ==========================================================
# 机器层探测业务逻辑（端口探测 + 熔断 + 告警风暴抑制）
# ==========================================================

async def execute_machine_probe(machine_id: int) -> MachineProbeHistory:
    """执行单个机器节点的 TCP 端口连通性探测 (无锁纯异步网络分离模式)"""
    # 1. 快速只读提取机器网络参数与历史防抖状态 (毫秒级释放数据库连接)
    with Session(engine) as session:
        machine = session.get(MachineNode, machine_id)
        if not machine:
            raise ValueError(f"MachineNode {machine_id} not found")
        host = machine.host
        port = machine.port
        name = machine.name
        retry_threshold = machine.retry_threshold or 3
        silence_minutes = machine.silence_minutes or 30
        email_receivers = list(machine.email_receivers or [])
        prev_status = machine.current_status
        prev_failures = machine.consecutive_failures or 0
        last_alert_at = machine.last_alert_at

    # 2. 在没有任何数据库会话占用的情况下执行纯异步网络探活 (完全杜绝 SQLite 锁争用)
    tcp_ok, tcp_ms, tcp_err = await check_tcp(host, port)
    now = datetime.utcnow()

    # 3. 快速开启微事务，持久化状态并立即提交
    with Session(engine) as session:
        machine = session.get(MachineNode, machine_id)
        if not machine:
            raise ValueError(f"MachineNode {machine_id} not found")
        apis = session.exec(select(ApiProbe).where(ApiProbe.machine_id == machine.id)).all()

        if tcp_ok:
            # 机器恢复上线逻辑
            if prev_status == "OFFLINE":
                if email_receivers:
                    subject = f"🟢【SchemaPulse 已恢复】机器节点 {name} 恢复上线"
                    html = generate_machine_recovery_email_html(
                        machine_name=name,
                        host=host,
                        port=port,
                        restored_apis_count=len(apis)
                    )
                    asyncio.create_task(send_email_notification(email_receivers, subject, html))
                
                # 解除名下接口熔断
                for api in apis:
                    if api.current_status == "CIRCUIT_BROKEN":
                        api.current_status = "UNKNOWN"
                        session.add(api)

            machine.current_status = "ONLINE"
            machine.consecutive_failures = 0
            machine.last_tcp_latency_ms = tcp_ms
            machine.last_probed_at = now
        else:
            # 机器端口握手失败 -> 标记 DEGRADED/OFFLINE 并执行熔断与告警抑制
            machine.consecutive_failures = prev_failures + 1
            machine.last_tcp_latency_ms = tcp_ms
            machine.last_probed_at = now

            if machine.consecutive_failures >= retry_threshold:
                # 熔断名下所有接口
                for api in apis:
                    api.current_status = "CIRCUIT_BROKEN"
                    session.add(api)

                need_alert = True
                if last_alert_at:
                    elapsed = (now - last_alert_at).total_seconds() / 60.0
                    if elapsed < silence_minutes:
                        need_alert = False

                if need_alert:
                    if email_receivers:
                        subject = f"🚨【SchemaPulse 告警】机器节点 {name} 端口不可达并已熔断"
                        html = generate_machine_offline_email_html(
                            machine_name=name,
                            host=host,
                            port=port,
                            error_msg=tcp_err or "TCP 连接拒绝",
                            consecutive_failures=machine.consecutive_failures,
                            suspended_apis_count=len(apis)
                        )
                        asyncio.create_task(send_email_notification(email_receivers, subject, html))
                    machine.last_alert_at = now
                machine.current_status = "OFFLINE"
            else:
                machine.current_status = "DEGRADED"

        # 记录机器探测历史
        history = MachineProbeHistory(
            machine_id=machine.id,
            tcp_ok=tcp_ok,
            tcp_latency_ms=tcp_ms,
            error_message=tcp_err,
            probed_at=now
        )
        session.add(history)
        session.add(machine)
        session.commit()
        session.refresh(history)
        return history


# ==========================================================
# 接口层探测业务逻辑（熔断短路检查 + HTTP + Schema 校验）
# ==========================================================

async def execute_api_probe(api_probe_id: int) -> ApiProbeHistory:
    """执行单个接口探针的业务校验 (带宿主机器离线熔断短路守卫，数据库非阻塞架构)"""
    # 1. 快速读取接口与对应机器静态信息
    with Session(engine) as session:
        api = session.get(ApiProbe, api_probe_id)
        if not api:
            raise ValueError(f"ApiProbe {api_probe_id} not found")

        machine = session.get(MachineNode, api.machine_id)
        if not machine:
            raise ValueError(f"MachineNode {api.machine_id} not found for ApiProbe {api_probe_id}")

        machine_status = machine.current_status
        machine_host = machine.host
        machine_port = machine.port
        machine_base_url = machine.base_url
        machine_last_tcp_ms = machine.last_tcp_latency_ms
        machine_id = machine.id

        api_id = api.id
        api_name = api.name
        api_base_url = api.base_url
        api_http_path = api.http_path
        api_http_method = api.http_method
        api_http_params = list(api.http_params or [])
        api_http_headers = api.http_headers or {}
        api_http_body_type = api.http_body_type or "none"
        api_http_body = api.http_body
        api_auth_type = api.auth_type or "none"
        api_auth_config = dict(api.auth_config or {})
        api_expected_schema = dict(api.expected_schema or {})
        api_retry_threshold = api.retry_threshold or 3
        api_silence_minutes = api.silence_minutes or 30
        api_email_receivers = list(api.email_receivers or [])
        prev_status = api.current_status
        prev_failures = api.consecutive_failures or 0
        last_alert_at = api.last_alert_at

    now = datetime.utcnow()

    # 2. 【核心熔断短路规则】：若宿主机器处于 OFFLINE 状态，直接短路
    if machine_status == "OFFLINE":
        with Session(engine) as session:
            api = session.get(ApiProbe, api_id)
            if api:
                api.current_status = "CIRCUIT_BROKEN"
                api.last_probed_at = now
                session.add(api)
            history = ApiProbeHistory(
                api_probe_id=api_id,
                machine_id=machine_id,
                circuit_broken=True,
                http_status_code=None,
                http_latency_ms=None,
                schema_matched=False,
                raw_response_snippet="[熔断短路] 宿主机器已离线，跳过发起网络请求",
                is_healthy=False,
                probed_at=now
            )
            session.add(history)
            session.commit()
            session.refresh(history)
            return history

    # 3. 机器在线 -> 解析 Postman 请求结构 (鉴权 Token、动态宏变量替换、Params/Headers/Body 组装)
    auth_token = None
    if api_auth_type == "bearer":
        auth_token = api_auth_config.get("token")

    # 组装与渲染动态 Header
    req_headers = parse_headers_to_dict(api_http_headers, auth_token=auth_token)
    if api_auth_type == "bearer" and auth_token:
        if "authorization" not in [k.lower() for k in req_headers]:
            req_headers["Authorization"] = f"Bearer {auth_token}"
    elif api_auth_type == "basic":
        u = api_auth_config.get("username", "")
        p = api_auth_config.get("password", "")
        if u or p:
            import base64
            b64_val = base64.b64encode(f"{u}:{p}".encode()).decode()
            if "authorization" not in [k.lower() for k in req_headers]:
                req_headers["Authorization"] = f"Basic {b64_val}"

    # 组装与渲染动态 Params
    req_params = parse_params_to_dict(api_http_params, auth_token=auth_token)

    # 组装与渲染动态 Body
    rendered_body = render_macro_string(api_http_body, auth_token=auth_token) if api_http_body else None

    # 计算目标 URL (优先使用接口自定义 base_url，次优先使用机器基准 base_url，否则降级使用机器宿主地址)
    rendered_path = render_macro_string(api_http_path, auth_token=auth_token)
    if not rendered_path.startswith("/"):
        rendered_path = "/" + rendered_path

    effective_base = api_base_url or machine_base_url
    if effective_base and effective_base.strip():
        base_clean = effective_base.strip().rstrip('/')
        url = f"{base_clean}{rendered_path}"
    else:
        scheme = "https" if machine_port == 443 else "http"
        url = (
            f"{scheme}://{machine_host}:{machine_port}{rendered_path}"
            if machine_port not in [80, 443]
            else f"{scheme}://{machine_host}{rendered_path}"
        )

    http_ok, http_code, http_ms, json_data, http_err = await check_http(
        url,
        method=api_http_method,
        headers=req_headers,
        params=req_params if req_params else None,
        body=rendered_body,
        body_type=api_http_body_type
    )

    schema_matched = False
    schema_errors = []
    raw_snippet = None

    if json_data is not None:
        raw_snippet = json.dumps(json_data, ensure_ascii=False)[:500]
        if http_ok:
            schema_matched, schema_errors = check_schema(json_data, api_expected_schema)
    else:
        schema_matched = False
        schema_errors = [{"field": "$root", "validator": "empty", "message": http_err or "未收到有效 JSON 响应"}]

    is_healthy = bool(http_ok and (http_code == 200) and schema_matched)

    # 4. 快速持久化校验结果与状态变更
    with Session(engine) as session:
        api = session.get(ApiProbe, api_id)
        if not api:
            raise ValueError(f"ApiProbe {api_id} not found")

        if is_healthy:
            if prev_status in ["DOWN", "DEGRADED"]:
                if api_email_receivers:
                    subject = f"🟢【SchemaPulse 已恢复】接口 {api_name} 契约校验恢复正常"
                    html = generate_recovery_email_html(api_name, f"{machine_host}:{machine_port}{api_http_path}")
                    asyncio.create_task(send_email_notification(api_email_receivers, subject, html))

            api.current_status = "HEALTHY"
            api.consecutive_failures = 0
        else:
            api.consecutive_failures = prev_failures + 1
            if api.consecutive_failures >= api_retry_threshold:
                need_alert = True
                if last_alert_at:
                    elapsed = (now - last_alert_at).total_seconds() / 60.0
                    if elapsed < api_silence_minutes:
                        need_alert = False

                if need_alert:
                    reasons = []
                    if http_code != 200:
                        reasons.append(f"HTTP状态码({http_code})")
                    if not schema_matched:
                        reasons.append("Schema破坏性变更")

                    if api_email_receivers:
                        subject = f"🚨【SchemaPulse 告警】接口 {api_name} 发生破坏性变更"
                        html = generate_alert_email_html(
                            target_name=api_name,
                            target_addr=f"{machine_host}:{machine_port}{api_http_path}",
                            failure_reasons=reasons,
                            consecutive_failures=api.consecutive_failures,
                            tcp_info=(True, machine_last_tcp_ms),
                            http_info=(http_code, http_ms),
                            schema_errors=schema_errors,
                            raw_snippet=raw_snippet or ""
                        )
                        asyncio.create_task(send_email_notification(api_email_receivers, subject, html))
                    api.last_alert_at = now
                api.current_status = "DOWN"
            else:
                api.current_status = "DEGRADED"

        api.last_http_code = http_code
        api.last_http_latency_ms = http_ms
        api.last_schema_matched = schema_matched
        api.last_probed_at = now

        history = ApiProbeHistory(
            api_probe_id=api.id,
            machine_id=machine_id,
            circuit_broken=False,
            http_status_code=http_code,
            http_latency_ms=http_ms,
            schema_matched=schema_matched,
            schema_diff_detail=schema_errors if schema_errors else None,
            raw_response_snippet=raw_snippet,
            is_healthy=is_healthy,
            probed_at=now
        )
        session.add(history)
        session.add(api)
        session.commit()
        session.refresh(history)
        return history


# ==========================================================
# 向下兼容旧版平铺目标探测入口
# ==========================================================

async def execute_probe_for_target(target_id: int) -> ProbeHistory:
    """旧版单层目标的探测逻辑 (非阻塞事务架构)"""
    with Session(engine) as session:
        target = session.get(MonitorTarget, target_id)
        if not target:
            raise ValueError(f"Target {target_id} not found")
        host = target.host
        port = target.port
        path = target.http_path
        method = target.http_method
        headers = dict(target.http_headers or {})
        expected_schema = dict(target.expected_schema or {})
        retry_threshold = target.retry_threshold or 3
        prev_failures = target.consecutive_failures or 0

    # 脱离 DB 会话进行探测
    tcp_ok, tcp_ms, tcp_err = await check_tcp(host, port)
    http_code = None
    http_ms = None
    json_data = None
    schema_matched = False
    schema_errors = []
    raw_snippet = None

    if tcp_ok:
        scheme = "https" if port == 443 else "http"
        url = f"{scheme}://{host}:{port}{path}" if (port not in [80, 443]) else f"{scheme}://{host}{path}"
        http_ok, http_code, http_ms, json_data, http_err = await check_http(
            url, method=method, headers=headers
        )
        if json_data is not None:
            raw_snippet = json.dumps(json_data, ensure_ascii=False)[:500]
            if http_ok:
                schema_matched, schema_errors = check_schema(json_data, expected_schema)
        else:
            schema_matched = False
            schema_errors = [{"field": "$root", "validator": "empty", "message": "未收到有效 JSON 响应"}]
    else:
        schema_matched = False
        schema_errors = [{"field": "$root", "validator": "tcp", "message": tcp_err or "TCP 连接拒绝"}]

    is_healthy = bool(tcp_ok and (http_code == 200) and schema_matched)
    now = datetime.utcnow()

    # 持久化结果
    with Session(engine) as session:
        target = session.get(MonitorTarget, target_id)
        if not target:
            raise ValueError(f"Target {target_id} not found")

        if is_healthy:
            target.current_status = "HEALTHY"
            target.consecutive_failures = 0
        else:
            target.consecutive_failures = prev_failures + 1
            target.current_status = "DOWN" if target.consecutive_failures >= retry_threshold else "DEGRADED"

        target.last_latency_ms = round(http_ms if http_ms is not None else (tcp_ms or 0.0), 2) if (tcp_ms is not None or http_ms is not None) else None
        target.last_tcp_latency_ms = round(tcp_ms, 2) if tcp_ms is not None else None
        target.last_http_latency_ms = round(http_ms, 2) if http_ms is not None else None
        target.last_probed_at = now

        history = ProbeHistory(
            target_id=target.id,
            tcp_ok=tcp_ok,
            tcp_latency_ms=tcp_ms,
            http_status_code=http_code,
            http_latency_ms=http_ms,
            schema_matched=schema_matched,
            schema_diff_detail=schema_errors if schema_errors else None,
            raw_response_snippet=raw_snippet,
            is_healthy=is_healthy,
            probed_at=now
        )
        session.add(history)
        session.add(target)
        session.commit()
        session.refresh(history)
        return history

