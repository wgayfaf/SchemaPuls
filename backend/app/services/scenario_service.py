"""scenario_service.py — 场景拨测执行引擎 (业务链路多步骤编排执行)

核心语义:
  1. 业务节点按定义顺序串行执行, 任一业务节点失败即中断链路 (后续业务节点标记 skipped)
  2. 清理步骤 (is_cleanup=True) 无论成败均执行 (finally 语义), 保证测试数据不残留
  3. 场景级共享变量池: 任一节点后置操作的 extract_variable 提取结果注入变量池,
     后续节点在路径/Params/Headers/Body 中通过 {{变量名}} 宏直接引用, 实现链路参数传递
  4. 健康判定: 所有业务节点全部通过才判定 HEALTHY (清理步骤不参与判定)
"""
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select

from app.models import Environment, ServiceGroup, MachineNode, ScenarioProbe, ScenarioProbeHistory
from app.database import engine
from app.services.probe_service import check_http_detailed, check_schema
from app.services.template_engine import (
    render_macro_string,
    parse_params_to_dict,
    parse_headers_to_dict,
    resolve_path_variables,
)
from app.services.action_engine import execute_pre_actions, execute_post_actions


# ==========================================================
# 单步骤执行原子操作 (被场景引擎与单步调试接口共用)
# ==========================================================

def _resolve_base_url(base_url: Optional[str], machine: MachineNode) -> str:
    """解析步骤请求基准地址: 显式基准地址优先, 否则回退宿主机器 host:port"""
    effective = (base_url or (machine.base_url if machine else None) or "").strip()
    if effective:
        return effective.rstrip("/")
    if machine:
        scheme = "https" if machine.port == 443 else "http"
        if machine.port in [80, 443]:
            return f"{scheme}://{machine.host}"
        return f"{scheme}://{machine.host}:{machine.port}"
    return ""


async def execute_scenario_step(
    step: Dict[str, Any],
    base_url: str,
    variable_pool: Dict[str, Any],
    step_index: int = 0
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """执行业务链路中的单个步骤节点

    Args:
        step: 步骤配置 (name/http_method/http_path/http_params/http_headers/http_body_type/
              http_body/auth_type/auth_config/pre_actions/post_actions/is_cleanup)
        base_url: 请求基准地址
        variable_pool: 场景共享变量池 (链路传递 + 环境变量), 执行中会被提取变量就地更新
        step_index: 节点序号 (用于结果展示)

    Returns:
        (step_result: 节点执行明细 dict, updated_env_vars: 需持久化回环境变量池的键值, json_data: 完整 JSON 响应)
    """
    http_method = (step.get("http_method") or "GET").upper()
    http_path = step.get("http_path") or "/"
    http_params = step.get("http_params") or []
    http_headers = step.get("http_headers") or []
    http_body_type = (step.get("http_body_type") or "none").lower()
    if http_body_type in ("form_data", "form"):
        http_body_type = "form"
    elif http_body_type in ("raw", "json"):
        http_body_type = "json"
    else:
        http_body_type = "none"
    http_body = step.get("http_body")
    expected_schema = step.get("expected_schema") or None
    auth_type = step.get("auth_type") or "none"
    auth_config = dict(step.get("auth_config") or {})
    pre_actions = step.get("pre_actions") or []
    post_actions = step.get("post_actions") or []

    result: Dict[str, Any] = {
        "step_index": step_index,
        "name": step.get("name") or f"节点 {step_index + 1}",
        "http_method": http_method,
        "http_path": http_path,
        "is_cleanup": bool(step.get("is_cleanup")),
        "ok": False,
        "status_code": None,
        "latency_ms": None,
        "error": None,
        "request_url": None,
        "assertions_result": [],
        "assertions_summary": None,
        "extracted_variables": {},
        "response_snippet": None,
        "schema_configured": bool(expected_schema),
        "schema_matched": None,
        "schema_errors": [],
        "script_error": None,
    }

    # 1. 解析鉴权 Token (供宏 {{TOKEN}} 渲染)
    auth_token = None
    if auth_type == "bearer":
        auth_token = auth_config.get("token")

    # 2. 组装与渲染动态 Headers / Params / Body / Path
    req_headers = parse_headers_to_dict(http_headers, auth_token=auth_token)
    if auth_type == "bearer" and auth_token:
        if "authorization" not in [k.lower() for k in req_headers]:
            req_headers["Authorization"] = f"Bearer {auth_token}"
    elif auth_type == "basic":
        u = auth_config.get("username", "")
        p = auth_config.get("password", "")
        if u or p:
            import base64
            b64_val = base64.b64encode(f"{u}:{p}".encode()).decode()
            if "authorization" not in [k.lower() for k in req_headers]:
                req_headers["Authorization"] = f"Basic {b64_val}"
    elif auth_type == "custom_header":
        hk = (auth_config.get("header_key") or "").strip()
        hv = auth_config.get("header_value") or ""
        if hk and hk.lower() not in [k.lower() for k in req_headers]:
            req_headers[hk] = hv

    raw_params = parse_params_to_dict(http_params, auth_token=auth_token)
    rendered_body = render_macro_string(http_body, auth_token=auth_token) if http_body else None
    rendered_path = render_macro_string(http_path, auth_token=auth_token)
    if not rendered_path.startswith("/"):
        rendered_path = "/" + rendered_path

    # 3. 执行前置操作 (变量池作为 environment_variables 注入, 实现 {{链路变量}} 引用)
    final_headers, final_params, final_body, final_path, variables, pre_updated_env = execute_pre_actions(
        pre_actions=pre_actions,
        headers=req_headers,
        params=raw_params,
        body=rendered_body,
        path=rendered_path,
        auth_token=auth_token,
        environment_variables=variable_pool
    )

    # 前置操作生成变量后的路径变量兜底解析
    final_path, final_params = resolve_path_variables(final_path, final_params, variables)
    if not final_path.startswith("/"):
        final_path = "/" + final_path

    url = f"{base_url}{final_path}"
    result["request_url"] = url

    # 4. 发起 HTTP 请求
    http_ok, http_code, http_ms, json_data, http_err, resp_headers, resp_text = await check_http_detailed(
        url,
        method=http_method,
        headers=final_headers,
        params=final_params if final_params else None,
        body=final_body,
        body_type=http_body_type
    )
    result["status_code"] = http_code
    result["latency_ms"] = http_ms
    if http_err:
        result["error"] = http_err

    if json_data is not None:
        result["response_snippet"] = json.dumps(json_data, ensure_ascii=False)[:500]

    # Schema 契约校验 (与接口探针同规则: 未配置契约不参与健康判定, 避免空 Schema {} 接受一切的假象)
    if json_data is not None:
        if not expected_schema:
            result["schema_matched"] = None
        elif http_ok:
            matched, schema_errors = check_schema(json_data, expected_schema)
            result["schema_matched"] = matched
            result["schema_errors"] = schema_errors
    elif expected_schema:
        result["schema_matched"] = False
        result["schema_errors"] = [{"field": "$root", "validator": "empty", "message": http_err or "未收到有效 JSON 响应"}]

    # 5. 执行后置操作 (断言校验 + 变量提取)
    all_assertions_passed, assertions_result, extracted_vars, post_updated_env = execute_post_actions(
        post_actions=post_actions,
        status_code=http_code,
        latency_ms=http_ms,
        response_headers=resp_headers,
        response_data=json_data,
        response_text=resp_text,
        context_variables=variables,
        environment_variables=variable_pool
    )
    result["assertions_result"] = assertions_result
    result["assertions_summary"] = {
        "all_passed": all_assertions_passed,
        "total": len(assertions_result),
        "passed_count": sum(1 for a in assertions_result if a.get("passed", False))
    }
    result["extracted_variables"] = extracted_vars
    result["script_error"] = variables.get("_script_error")

    # 6. 健康判定: HTTP 成功 + Schema 契约未突变 + 全部断言通过
    result["ok"] = bool(http_ok and (http_code == 200) and (result["schema_matched"] is not False) and all_assertions_passed)

    # 7. 提取变量注入场景共享变量池 (供后续节点 {{引用}}), 并收集需持久化的环境变量
    variable_pool.update({k: v for k, v in extracted_vars.items() if k})
    updated_env: Dict[str, Any] = {}
    updated_env.update(pre_updated_env)
    updated_env.update(post_updated_env)

    return result, updated_env, json_data


# ==========================================================
# 场景整链执行引擎
# ==========================================================

async def execute_scenario_probe(scenario_id: int, trigger: str = "scheduled") -> ScenarioProbeHistory:
    """执行完整业务链路场景拨测

    执行流程:
      业务节点 1 -> 业务节点 2 -> ... -> 业务节点 N
        (任一节点失败则中断, 后续业务节点标记 skipped)
      -> 清理节点 [无论成败均执行, finally 语义]

    Returns:
        持久化后的 ScenarioProbeHistory 记录
    """
    # 1. 快照读取场景与机器上下文 (毫秒级释放数据库连接)
    with Session(engine) as session:
        scenario = session.get(ScenarioProbe, scenario_id)
        if not scenario:
            raise ValueError(f"ScenarioProbe {scenario_id} not found")
        machine = session.get(MachineNode, scenario.machine_id)
        if not machine:
            raise ValueError(f"MachineNode {scenario.machine_id} not found for ScenarioProbe {scenario_id}")

        grp = session.get(ServiceGroup, machine.group_id) if machine.group_id else None
        env = session.get(Environment, grp.environment_id) if grp and grp.environment_id else None
        env_id = env.id if env else None
        env_variables = dict(env.variables or {}) if env and env.variables else {}

        machine_status = machine.current_status
        base_url = _resolve_base_url(scenario.base_url, machine)
        scenario_name = scenario.name
        steps: List[Dict[str, Any]] = list(scenario.steps or [])

    now = datetime.utcnow()
    variable_pool: Dict[str, Any] = dict(env_variables)
    all_updated_env: Dict[str, Any] = {}

    # 2. 【熔断短路守卫】宿主机器离线时跳过整链网络请求
    if machine_status == "OFFLINE":
        with Session(engine) as session:
            scenario = session.get(ScenarioProbe, scenario_id)
            if scenario:
                scenario.current_status = "DOWN"
                scenario.last_run_at = now
                session.add(scenario)
            history = ScenarioProbeHistory(
                scenario_id=scenario_id,
                machine_id=scenario.machine_id if scenario else 0,
                trigger=trigger,
                is_success=False,
                total_latency_ms=None,
                steps_detail=[],
                error_message="[熔断短路] 宿主机器已离线, 跳过整链拨测",
                probed_at=now
            )
            session.add(history)
            session.commit()
            session.refresh(history)
            return history

    # 3. 分离业务节点与清理节点
    business_steps = [(idx, s) for idx, s in enumerate(steps) if not s.get("is_cleanup")]
    cleanup_steps = [(idx, s) for idx, s in enumerate(steps) if s.get("is_cleanup")]

    steps_detail: List[Dict[str, Any]] = []
    chain_aborted = False
    abort_reason = None
    perf_start = time.perf_counter()

    # 4. 串行执行业务节点 (任一失败即中断链路)
    for idx, step in business_steps:
        if chain_aborted:
            steps_detail.append({
                "step_index": idx,
                "name": step.get("name") or f"节点 {idx + 1}",
                "http_method": (step.get("http_method") or "GET").upper(),
                "http_path": step.get("http_path") or "/",
                "is_cleanup": False,
                "skipped": True,
                "ok": False,
                "error": "前序节点失败, 链路已中断"
            })
            continue
        try:
            step_result, updated_env, _resp = await execute_scenario_step(step, base_url, variable_pool, step_index=idx)
            all_updated_env.update(updated_env)
            steps_detail.append(step_result)
            if not step_result.get("ok"):
                chain_aborted = True
                abort_reason = f"节点 {idx + 1} [{step_result.get('name')}] 失败: {step_result.get('error') or '断言未全部通过'}"
        except Exception as step_err:
            chain_aborted = True
            abort_reason = f"节点 {idx + 1} 执行异常: {str(step_err)}"
            steps_detail.append({
                "step_index": idx,
                "name": step.get("name") or f"节点 {idx + 1}",
                "http_method": (step.get("http_method") or "GET").upper(),
                "http_path": step.get("http_path") or "/",
                "is_cleanup": False,
                "ok": False,
                "error": f"节点执行异常: {str(step_err)}"
            })

    # 5. 清理节点: 无论业务链路成败均执行 (finally 语义)
    for idx, step in cleanup_steps:
        try:
            step_result, updated_env, _resp = await execute_scenario_step(step, base_url, variable_pool, step_index=idx)
            all_updated_env.update(updated_env)
            steps_detail.append(step_result)
        except Exception as step_err:
            steps_detail.append({
                "step_index": idx,
                "name": step.get("name") or f"节点 {idx + 1}",
                "http_method": (step.get("http_method") or "GET").upper(),
                "http_path": step.get("http_path") or "/",
                "is_cleanup": True,
                "ok": False,
                "error": f"清理步骤执行异常: {str(step_err)}"
            })

    total_latency_ms = round((time.perf_counter() - perf_start) * 1000, 2)

    # 6. 健康判定: 所有业务节点全部通过 (清理步骤不参与判定)
    business_results = [d for d in steps_detail if not d.get("is_cleanup")]
    is_success = bool(business_results) and all(d.get("ok") for d in business_results)
    error_message = None if is_success else (abort_reason or "业务链路存在失败节点")

    # 7. 持久化执行结果与场景状态; 同步环境变量更新
    with Session(engine) as session:
        if all_updated_env and env_id:
            try:
                from sqlalchemy.orm.attributes import flag_modified
                env_record = session.get(Environment, env_id)
                if env_record:
                    curr_vars = dict(env_record.variables or {})
                    curr_vars.update(all_updated_env)
                    env_record.variables = curr_vars
                    flag_modified(env_record, "variables")
                    session.add(env_record)
            except Exception as env_err:
                print(f"[Warn] 场景拨测持久化更新环境变量失败: {env_err}")

        scenario = session.get(ScenarioProbe, scenario_id)
        if scenario:
            scenario.current_status = "HEALTHY" if is_success else "DOWN"
            scenario.last_run_at = now
            scenario.last_total_latency_ms = total_latency_ms
            session.add(scenario)

        history = ScenarioProbeHistory(
            scenario_id=scenario_id,
            machine_id=scenario.machine_id if scenario else 0,
            trigger=trigger,
            is_success=is_success,
            total_latency_ms=total_latency_ms,
            steps_detail=steps_detail,
            error_message=error_message,
            probed_at=now
        )
        session.add(history)
        session.commit()
        session.refresh(history)
        return history


def serialize_scenario_history(h: ScenarioProbeHistory) -> dict:
    """场景拨测历史流水序列化 (供前端结果抽屉渲染)"""
    return {
        "id": h.id,
        "scenario_id": h.scenario_id,
        "machine_id": h.machine_id,
        "trigger": h.trigger,
        "is_success": h.is_success,
        "total_latency_ms": h.total_latency_ms,
        "steps_detail": h.steps_detail or [],
        "error_message": h.error_message,
        "probed_at": h.probed_at.isoformat() if h.probed_at else None,
    }
