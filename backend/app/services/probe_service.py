import asyncio
import time
import json
import re
import platform
import subprocess
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
from app.services.action_engine import (
    execute_pre_actions,
    execute_post_actions
)


# ==========================================================
# 基础探测原子操作 (Ping 主机探活 + TCP 端口握手 + HTTP 业务请求)
# ==========================================================

def clean_host(raw_host: str) -> str:
    """清理主机名，剥离可能附带的协议前缀、尾部斜杠或端口号"""
    if not raw_host:
        return ""
    host = raw_host.strip()
    if host.startswith("http://"):
        host = host[7:]
    elif host.startswith("https://"):
        host = host[8:]
    host = host.split("/")[0]
    if ":" in host and not host.startswith("["):
        host = host.split(":")[0]
    return host


def _sync_ping(target: str, timeout_ms: int = 1000) -> Tuple[bool, Optional[float], Optional[str]]:
    """同步执行系统 ICMP Ping"""
    is_windows = platform.system().lower() == "windows"
    timeout_sec = max(1, int(round(timeout_ms / 1000.0)))
    cmd = ["ping", "-n", "1", "-w", str(timeout_ms), target] if is_windows else ["ping", "-c", "1", "-W", str(timeout_sec), target]
    
    start = time.perf_counter()
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            timeout=(timeout_ms / 1000.0) + 1.5
        )
        raw_out = res.stdout.decode("gbk" if is_windows else "utf-8", errors="ignore")
        
        # 判定失活特征
        is_failed = (
            res.returncode != 0 or
            "无法访问目标主机" in raw_out or
            "Destination host unreachable" in raw_out or
            "请求超时" in raw_out or
            "Request timed out" in raw_out or
            "100% 丢失" in raw_out or
            "100% loss" in raw_out.lower() or
            "General failure" in raw_out or
            "一般故障" in raw_out or
            "transmit failed" in raw_out.lower()
        )
        
        # 判定存活特征
        is_alive = (
            not is_failed and
            (
                "0% 丢失" in raw_out or
                "0% loss" in raw_out.lower() or
                "0% packet loss" in raw_out or
                "TTL=" in raw_out.upper() or
                "时间=" in raw_out or
                "time=" in raw_out.lower() or
                "<1ms" in raw_out
            )
        )
        
        if is_alive:
            lat_ms = None
            m = re.search(r'(?:时间|time)[=<]([\d\.]+)\s*ms', raw_out, re.I)
            if m:
                lat_ms = float(m.group(1))
            elif "<1ms" in raw_out:
                lat_ms = 0.5
            else:
                lat_ms = round((time.perf_counter() - start) * 1000, 2)
            return True, lat_ms, None
        else:
            return False, None, "目标主机不可达 (Ping 超时或未响应)"
            
    except subprocess.TimeoutExpired:
        return False, None, f"Ping 探测超时 ({timeout_ms}ms)"
    except Exception as e:
        return False, None, f"Ping 执行异常: {str(e)}"


async def check_ping(host: str, timeout_ms: int = 1000) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    通过系统 ICMP Ping 判断机器/IP 是否在线 (Host is alive)，非阻塞多线程执行
    返回: (ping_ok, ping_latency_ms, error_msg)
    """
    target = clean_host(host)
    if not target:
        return False, None, "目标主机地址为空"
    return await asyncio.to_thread(_sync_ping, target, timeout_ms)


async def check_tcp(host: str, port: int, timeout: float = 2.0) -> Tuple[bool, Optional[float], Optional[str]]:
    """TCP Socket 握手连通性与耗时探测 (通过端口判断服务是否存在)"""
    target = clean_host(host)
    start = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(target, port),
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
        return False, latency_ms, f"端口连接超时 ({timeout}s)"
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return False, latency_ms, f"端口连接拒绝: {str(e)}"


async def check_http_detailed(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    body_type: str = "none",
    timeout: float = 5.0
) -> Tuple[bool, Optional[int], Optional[float], Optional[Dict[str, Any]], Optional[str], Dict[str, str], str]:
    """HTTP 业务请求探测 (返回包含 resp_headers 与 resp_text 的完整上下文以支持后置断言)"""
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
            resp_headers = dict(resp.headers)
            resp_text = resp.text
            is_ok = (resp.status_code == 200)
            err = None if is_ok else f"HTTP 状态码异常: {resp.status_code}"
            return is_ok, resp.status_code, latency_ms, json_data, err, resp_headers, resp_text
    except asyncio.CancelledError:
        raise
    except httpx.TimeoutException:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return False, None, latency_ms, None, f"HTTP 请求超时 ({timeout}s)", {}, ""
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return False, None, latency_ms, None, f"HTTP 请求异常: {str(e)}", {}, ""


async def check_http(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    body_type: str = "none",
    timeout: float = 5.0
) -> Tuple[bool, Optional[int], Optional[float], Optional[Dict[str, Any]], Optional[str]]:
    """向后兼容的 HTTP 探测包装函数"""
    is_ok, code, lat, jdata, err, _, _ = await check_http_detailed(
        url, method=method, headers=headers, params=params, body=body, body_type=body_type, timeout=timeout
    )
    return is_ok, code, lat, jdata, err


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
    """执行单个机器节点的双阶段网络探活 (1. Ping 判断机器是否在线 -> 2. 端口判断服务是否存在)"""
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

    # 2. 在脱离数据库会话的环境下执行纯异步双重网络探活 (完全杜绝 SQLite 锁争用)
    # 阶段一：通过 IP / Host 执行 ICMP Ping 判断机器物理/网络层是否在线 (Host is alive)
    ping_ok, ping_ms, ping_err = await check_ping(host, timeout_ms=1000)

    # 阶段二：若主机在线，则进一步通过端口探测服务是否存在 (Port is open)
    if ping_ok:
        tcp_ok, tcp_ms, tcp_err = await check_tcp(host, port, timeout=2.0)
    else:
        tcp_ok = False
        tcp_ms = None
        tcp_err = ping_err or "目标主机不可达 (Ping 超时或未响应)"

    now = datetime.utcnow()

    # 综合推断判定逻辑:
    # 1. 主机不可达 (Ping 失败) -> 机器判定为 OFFLINE
    # 2. 主机在线且端口握手正常 (Ping 通 + TCP 通) -> 机器判定为 ONLINE
    # 3. 主机在线但端口不通 (Ping 通 + TCP 失败) -> 机器判定为 DEGRADED (主机在线但服务未开启/未监听)
    if not ping_ok:
        is_success = False
        overall_status = "OFFLINE"
        diagnostic_msg = ping_err or "目标主机不可达 (Ping 超时或未响应)"
        effective_latency = None
    elif tcp_ok:
        is_success = True
        overall_status = "ONLINE"
        diagnostic_msg = None
        effective_latency = tcp_ms if (tcp_ms and tcp_ms > 0) else ping_ms
    else:
        is_success = False
        overall_status = "DEGRADED"
        diagnostic_msg = f"主机在线 (Ping {ping_ms}ms)，但服务端口 {port} 连接失败: {tcp_err}"
        effective_latency = ping_ms

    # 3. 快速开启微事务，持久化状态并立即提交
    with Session(engine) as session:
        machine = session.get(MachineNode, machine_id)
        if not machine:
            raise ValueError(f"MachineNode {machine_id} not found")
        apis = session.exec(select(ApiProbe).where(ApiProbe.machine_id == machine.id)).all()

        if is_success:
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
            machine.ping_ok = True
            machine.last_ping_latency_ms = ping_ms
            machine.tcp_ok = True
            machine.last_tcp_latency_ms = effective_latency
            machine.last_error_message = None
            machine.last_probed_at = now
        else:
            # 机器探活异常（Ping 不通 或 端口连接失败）
            machine.consecutive_failures = prev_failures + 1
            machine.ping_ok = ping_ok
            machine.last_ping_latency_ms = ping_ms
            machine.tcp_ok = tcp_ok
            machine.last_tcp_latency_ms = effective_latency
            machine.last_error_message = diagnostic_msg
            machine.last_probed_at = now

            if overall_status == "OFFLINE" or machine.consecutive_failures >= retry_threshold:
                machine.current_status = "OFFLINE"
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
                        subject = f"🚨【SchemaPulse 告警】机器节点 {name} 不可达并已熔断"
                        html = generate_machine_offline_email_html(
                            machine_name=name,
                            host=host,
                            port=port,
                            error_msg=diagnostic_msg,
                            consecutive_failures=machine.consecutive_failures,
                            suspended_apis_count=len(apis)
                        )
                        asyncio.create_task(send_email_notification(email_receivers, subject, html))
                    machine.last_alert_at = now
            else:
                machine.current_status = overall_status

        # 记录机器探测历史流水
        history = MachineProbeHistory(
            machine_id=machine.id,
            ping_ok=ping_ok,
            ping_latency_ms=ping_ms,
            tcp_ok=tcp_ok,
            tcp_latency_ms=tcp_ms,
            error_message=diagnostic_msg,
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
        api_pre_actions = list(api.pre_actions or [])
        api_post_actions = list(api.post_actions or [])
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

    # 3. 机器在线 -> 解析 Postman 请求结构 (鉴权 Token、前置操作、动态宏变量替换、Params/Headers/Body 组装)
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

    # 路径渲染预处理
    rendered_path = render_macro_string(api_http_path, auth_token=auth_token)
    if not rendered_path.startswith("/"):
        rendered_path = "/" + rendered_path

    # 执行【前置操作 (Pre-request Actions)】：动态变量、请求头注入、参数注入及前置脚本
    final_headers, final_params, final_body, final_path, variables = execute_pre_actions(
        pre_actions=api_pre_actions,
        headers=req_headers,
        params=req_params,
        body=rendered_body,
        path=rendered_path,
        auth_token=auth_token
    )

    if not final_path.startswith("/"):
        final_path = "/" + final_path

    effective_base = api_base_url or machine_base_url
    if effective_base and effective_base.strip():
        base_clean = effective_base.strip().rstrip('/')
        url = f"{base_clean}{final_path}"
    else:
        scheme = "https" if machine_port == 443 else "http"
        url = (
            f"{scheme}://{machine_host}:{machine_port}{final_path}"
            if machine_port not in [80, 443]
            else f"{scheme}://{machine_host}{final_path}"
        )

    # 发起 HTTP 业务请求探测并返回完整上下文
    http_ok, http_code, http_ms, json_data, http_err, resp_headers, resp_text = await check_http_detailed(
        url,
        method=api_http_method,
        headers=final_headers,
        params=final_params if final_params else None,
        body=final_body,
        body_type=api_http_body_type
    )

    # 执行 Schema 校验
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

    # 执行【后置操作 (Post-response Actions / Assertions)】
    all_assertions_passed, assertions_result, extracted_vars = execute_post_actions(
        post_actions=api_post_actions,
        status_code=http_code,
        latency_ms=http_ms,
        response_headers=resp_headers,
        response_data=json_data,
        response_text=resp_text,
        context_variables=variables
    )

    is_healthy = bool(http_ok and (http_code == 200) and schema_matched and all_assertions_passed)

    # 4. 快速持久化校验结果与状态变更
    with Session(engine) as session:
        api = session.get(ApiProbe, api_id)
        if not api:
            raise ValueError(f"ApiProbe {api_id} not found")

        if is_healthy:
            if prev_status in ["DOWN", "DEGRADED"]:
                if api_email_receivers:
                    subject = f"🟢【SchemaPulse 已恢复】接口 {api_name} 契约与断言校验恢复正常"
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
                    if not all_assertions_passed:
                        failed_asserts = [a.get("name", "断言失败") for a in assertions_result if not a.get("passed", False)]
                        reasons.append(f"后置断言未通过({', '.join(failed_asserts[:2])})")

                    if api_email_receivers:
                        subject = f"🚨【SchemaPulse 告警】接口 {api_name} 探测未通过"
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
            assertions_result=assertions_result if assertions_result else None,
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

