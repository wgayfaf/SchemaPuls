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
    except Exception as e:
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return False, latency_ms, f"TCP 连接失败: {str(e)}"


async def check_http(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 5.0
) -> Tuple[bool, Optional[int], Optional[float], Optional[Dict[str, Any]], Optional[str]]:
    """HTTP 业务请求探测"""
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
            resp = await client.request(method, url, headers=headers)
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            try:
                json_data = resp.json()
            except Exception:
                json_data = None
            is_ok = (resp.status_code == 200)
            err = None if is_ok else f"HTTP 状态码异常: {resp.status_code}"
            return is_ok, resp.status_code, latency_ms, json_data, err
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
    """执行单个机器节点的 TCP 端口连通性探测"""
    with Session(engine) as session:
        machine = session.get(MachineNode, machine_id)
        if not machine:
            raise ValueError(f"MachineNode {machine_id} not found")

        # 1. 探测 TCP 端口连通性
        tcp_ok, tcp_ms, tcp_err = await check_tcp(machine.host, machine.port)
        now = datetime.utcnow()
        prev_status = machine.current_status

        # 查询名下所有接口探针
        apis = session.exec(select(ApiProbe).where(ApiProbe.machine_id == machine.id)).all()

        if tcp_ok:
            # 机器恢复上线逻辑
            if prev_status == "OFFLINE":
                if machine.email_receivers:
                    subject = f"🟢【SchemaPulse 已恢复】机器节点 {machine.name} 恢复上线"
                    html = generate_machine_recovery_email_html(
                        machine_name=machine.name,
                        host=machine.host,
                        port=machine.port,
                        restored_apis_count=len(apis)
                    )
                    asyncio.create_task(send_email_notification(machine.email_receivers, subject, html))
                
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
            # 机器端口握手失败 -> 标记 OFFLINE 并执行熔断与告警抑制
            machine.consecutive_failures += 1
            machine.last_tcp_latency_ms = tcp_ms
            machine.last_probed_at = now

            # 熔断名下所有接口 (不发起任何实际 HTTP 请求)
            for api in apis:
                api.current_status = "CIRCUIT_BROKEN"
                session.add(api)

            if machine.consecutive_failures >= machine.retry_threshold:
                need_alert = True
                if machine.last_alert_at:
                    elapsed = (now - machine.last_alert_at).total_seconds() / 60.0
                    if elapsed < machine.silence_minutes:
                        need_alert = False

                if need_alert:
                    if machine.email_receivers:
                        subject = f"🚨【SchemaPulse 告警】机器节点 {machine.name} 端口不可达并已熔断"
                        html = generate_machine_offline_email_html(
                            machine_name=machine.name,
                            host=machine.host,
                            port=machine.port,
                            error_msg=tcp_err or "TCP 连接拒绝",
                            consecutive_failures=machine.consecutive_failures,
                            suspended_apis_count=len(apis)
                        )
                        asyncio.create_task(send_email_notification(machine.email_receivers, subject, html))
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
    """执行单个接口探针的业务校验 (带宿主机器离线熔断短路守卫)"""
    with Session(engine) as session:
        api = session.get(ApiProbe, api_probe_id)
        if not api:
            raise ValueError(f"ApiProbe {api_probe_id} not found")

        machine = session.get(MachineNode, api.machine_id)
        if not machine:
            raise ValueError(f"MachineNode {api.machine_id} not found for ApiProbe {api_probe_id}")

        now = datetime.utcnow()

        # 【核心熔断短路规则】：若机器已离线，直接短路，绝不发起真实 HTTP 网络请求！
        if machine.current_status == "OFFLINE":
            api.current_status = "CIRCUIT_BROKEN"
            api.last_probed_at = now
            session.add(api)

            history = ApiProbeHistory(
                api_probe_id=api.id,
                machine_id=machine.id,
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

        # 机器在线 -> 继承机器 host 与 port 发起真实 HTTP 请求
        scheme = "https" if machine.port == 443 else "http"
        url = (
            f"{scheme}://{machine.host}:{machine.port}{api.http_path}"
            if machine.port not in [80, 443]
            else f"{scheme}://{machine.host}{api.http_path}"
        )

        http_ok, http_code, http_ms, json_data, http_err = await check_http(
            url, method=api.http_method, headers=api.http_headers
        )

        schema_matched = False
        schema_errors = []
        raw_snippet = None

        if json_data is not None:
            raw_snippet = json.dumps(json_data, ensure_ascii=False)[:500]
            if http_ok:
                schema_matched, schema_errors = check_schema(json_data, api.expected_schema)
        else:
            schema_matched = False
            schema_errors = [{"field": "$root", "validator": "empty", "message": http_err or "未收到有效 JSON 响应"}]

        is_healthy = bool(http_ok and (http_code == 200) and schema_matched)

        # 评估接口健康状态机
        prev_status = api.current_status
        if is_healthy:
            if prev_status in ["DOWN", "DEGRADED"]:
                if api.email_receivers:
                    subject = f"🟢【SchemaPulse 已恢复】接口 {api.name} 契约校验恢复正常"
                    html = generate_recovery_email_html(api.name, f"{machine.host}:{machine.port}{api.http_path}")
                    asyncio.create_task(send_email_notification(api.email_receivers, subject, html))

            api.current_status = "HEALTHY"
            api.consecutive_failures = 0
        else:
            api.consecutive_failures += 1
            if api.consecutive_failures >= api.retry_threshold:
                need_alert = True
                if api.last_alert_at:
                    elapsed = (now - api.last_alert_at).total_seconds() / 60.0
                    if elapsed < api.silence_minutes:
                        need_alert = False

                if need_alert:
                    reasons = []
                    if http_code != 200:
                        reasons.append(f"HTTP状态码({http_code})")
                    if not schema_matched:
                        reasons.append("Schema破坏性变更")

                    if api.email_receivers:
                        subject = f"🚨【SchemaPulse 告警】接口 {api.name} 发生破坏性变更"
                        html = generate_alert_email_html(
                            target_name=api.name,
                            target_addr=f"{machine.host}:{machine.port}{api.http_path}",
                            failure_reasons=reasons,
                            consecutive_failures=api.consecutive_failures,
                            tcp_info=(True, machine.last_tcp_latency_ms),
                            http_info=(http_code, http_ms),
                            schema_errors=schema_errors,
                            raw_snippet=raw_snippet or ""
                        )
                        asyncio.create_task(send_email_notification(api.email_receivers, subject, html))
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
            machine_id=machine.id,
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
    """旧版单层目标的探测逻辑 (兼容过渡)"""
    with Session(engine) as session:
        target = session.get(MonitorTarget, target_id)
        if not target:
            raise ValueError(f"Target {target_id} not found")

        tcp_ok, tcp_ms, tcp_err = await check_tcp(target.host, target.port)
        http_code = None
        http_ms = None
        json_data = None
        schema_matched = False
        schema_errors = []
        raw_snippet = None

        if tcp_ok:
            scheme = "https" if target.port == 443 else "http"
            url = f"{scheme}://{target.host}:{target.port}{target.http_path}" if (target.port not in [80, 443]) else f"{scheme}://{target.host}{target.http_path}"
            http_ok, http_code, http_ms, json_data, http_err = await check_http(
                url, method=target.http_method, headers=target.http_headers
            )
            if json_data is not None:
                raw_snippet = json.dumps(json_data, ensure_ascii=False)[:500]
                if http_ok:
                    schema_matched, schema_errors = check_schema(json_data, target.expected_schema)
            else:
                schema_matched = False
                schema_errors = [{"field": "$root", "validator": "empty", "message": "未收到有效 JSON 响应"}]
        else:
            schema_matched = False
            schema_errors = [{"field": "$root", "validator": "tcp", "message": tcp_err or "TCP 连接拒绝"}]

        is_healthy = bool(tcp_ok and (http_code == 200) and schema_matched)
        now = datetime.utcnow()

        if is_healthy:
            target.current_status = "HEALTHY"
            target.consecutive_failures = 0
        else:
            target.consecutive_failures += 1
            target.current_status = "DOWN" if target.consecutive_failures >= target.retry_threshold else "DEGRADED"

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
