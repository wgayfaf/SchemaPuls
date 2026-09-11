#!/usr/bin/env python3
"""
SchemaPulse - 阶段 0 原型验证脚本 (Standalone Probe MVP)
功能：
1. 异步 TCP 端口握手探活 (测量延迟)
2. 异步 HTTP 请求 (检查状态码 200)
3. JSON Schema 深度断言 (检测字段缺失、类型改变、多余未知字段)
4. 告警格式化与邮件 HTML/控制台推送模拟
"""

import asyncio
import time
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import httpx
from jsonschema import Draft7Validator

# 确保在 Windows 控制台环境下输出 UTF-8 字符不报错
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


async def check_tcp(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, Optional[float], Optional[str]]:
    """TCP 握手探活"""
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
    """HTTP 请求探测"""
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
            resp = await client.request(method, url, headers=headers)
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            
            # 尝试解析 JSON
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
    """JSON Schema 严格断言，提取破坏性变更"""
    if json_data is None:
        return False, [{"field": "$root", "message": "响应内容不是合法的 JSON 对象"}]

    validator = Draft7Validator(expected_schema)
    errors = []

    for err in validator.iter_errors(json_data):
        field_path = ".".join([str(p) for p in err.absolute_path]) or "$root"
        err_type = err.validator
        
        # 破坏性变更分类
        if err_type == "required":
            detail = f"必填字段缺失: {err.message}"
        elif err_type == "type":
            detail = f"字段类型不匹配: {err.message}"
        elif err_type == "additionalProperties":
            detail = f"检测到未声明的新增字段: {err.message}"
        else:
            detail = err.message

        errors.append({
            "field": field_path,
            "validator": err_type,
            "message": detail
        })

    return (len(errors) == 0), errors


def print_email_preview(
    receivers: List[str],
    subject: str,
    target_name: str,
    target_addr: str,
    failure_reasons: List[str],
    tcp_info: Tuple[bool, Optional[float]],
    http_info: Tuple[Optional[int], Optional[float]],
    schema_errors: List[Dict[str, Any]],
    raw_snippet: str = ""
):
    """展示生成的结构化告警邮件内容预览"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reasons_str = "、".join(failure_reasons)

    print("\n" + "=" * 60)
    print(f"【📧 告警邮件生成与推送预览】")
    print(f"收件人列表: {receivers}")
    print(f"邮件主题  : {subject}")
    print("-" * 60)
    print(f"监控目标  : {target_name} ({target_addr})")
    print(f"检测时间  : {now_str}")
    print(f"故障原因  : {reasons_str}")
    print(f"TCP 连通  : {'[OK]' if tcp_info[0] else '[FAIL]'} ({tcp_info[1]}ms)")
    print(f"HTTP 状态 : {http_info[0]} ({http_info[1]}ms)")
    print(f"Schema状态: {'[FAIL] 破坏性变更' if schema_errors else '[OK]'}")
    
    if schema_errors:
        print("\n[破坏性变更明细列表]:")
        for err in schema_errors:
            print(f"  * 字段路径: {err['field']} | 错误类型: {err['validator']} | 详情: {err['message']}")

    if raw_snippet:
        print(f"\n[现场响应截取]:\n{raw_snippet[:260]}...")
    print("=" * 60 + "\n")


async def run_single_probe(
    name: str,
    host: str,
    port: int,
    path: str,
    expected_schema: Dict[str, Any],
    email_receivers: Optional[List[str]] = None
):
    """运行一次端到端探测"""
    print(f"\n[START] 开始探测目标: [{name}] ({host}:{port}{path})...")
    is_healthy = True
    failure_reasons = []

    # 1. TCP 探活
    tcp_ok, tcp_ms, tcp_err = await check_tcp(host, port)
    print(f"  [1/3] TCP 连通性: {'OK' if tcp_ok else 'FAIL'} (耗时: {tcp_ms}ms)")
    if not tcp_ok:
        is_healthy = False
        failure_reasons.append(tcp_err or "TCP 握手超时")

    # 2. HTTP 检查 (若 TCP 通畅才继续，或协议走 443 时自动用 https)
    http_code = None
    http_ms = None
    json_data = None
    schema_errors = []

    if tcp_ok:
        scheme = "https" if port == 443 else "http"
        url = f"{scheme}://{host}:{port}{path}" if (port not in [80, 443]) else f"{scheme}://{host}{path}"
        
        http_ok, http_code, http_ms, json_data, http_err = await check_http(url)
        print(f"  [2/3] HTTP 请求: 状态码 {http_code} (耗时: {http_ms}ms)")
        if not http_ok:
            is_healthy = False
            failure_reasons.append(http_err or f"HTTP 响应状态码非 200: {http_code}")

        # 3. Schema 校验
        if http_ok and json_data is not None:
            schema_ok, schema_errors = check_schema(json_data, expected_schema)
            print(f"  [3/3] Schema 校验: {'通过' if schema_ok else '未通过 (捕获破坏性变更)'}")
            if not schema_ok:
                is_healthy = False
                failure_reasons.append(f"发现 {len(schema_errors)} 处破坏性结构变更")
                for err in schema_errors:
                    print(f"        👉 {err['field']}: {err['message']}")
    else:
        print("  [跳过] 由于 TCP 端口未开放，跳过 HTTP 与 Schema 校验。")

    # 触发告警
    if not is_healthy:
        raw_str = json.dumps(json_data, ensure_ascii=False, indent=2) if json_data else ""
        receivers = email_receivers or ["dev-team@company.com", "ops-lead@company.com"]
        subject = f"🚨【SchemaPulse 告警】监控目标 [{name}] 发生服务异常/结构破坏性变更"
        print_email_preview(
            receivers=receivers,
            subject=subject,
            target_name=name,
            target_addr=f"{host}:{port}{path}",
            failure_reasons=failure_reasons,
            tcp_info=(tcp_ok, tcp_ms),
            http_info=(http_code, http_ms),
            schema_errors=schema_errors,
            raw_snippet=raw_str
        )
    else:
        print(f"  [OK] 目标 [{name}] 全部健康检查通过！")


# ---------------- 测试运行用例 ----------------
async def main():
    print("==================================================")
    print("   SchemaPulse - 原型阶段 0 探针演示")
    print("==================================================")

    # 示例 1: 正常接口测试 (测试公网 httpbin 接口)
    schema_v1 = {
        "type": "object",
        "required": ["headers", "origin", "url"],
        "properties": {
            "origin": {"type": "string"},
            "url": {"type": "string"},
            "headers": {"type": "object"}
        }
    }
    
    await run_single_probe(
        name="公网测试网关 (预期健康)",
        host="httpbin.org",
        port=80,
        path="/get",
        expected_schema=schema_v1
    )

    # 示例 2: 模拟【破坏性结构变更】（例如要求必须有 status_code 字段，且不允许未知字段）
    broken_schema = {
        "type": "object",
        "required": ["headers", "origin", "url", "non_existing_token"],  # 故意要求一个不存在的字段
        "properties": {
            "origin": {"type": "number"},  # 故意将 string 写成 number
            "url": {"type": "string"},
            "headers": {"type": "object"}
        },
        "additionalProperties": False  # 严格模式：不允许其它新增字段
    }

    print("\n--------------------------------------------------")
    print("正在演示【破坏性结构变更】场景告警触发...")
    await run_single_probe(
        name="业务数据接口 (模拟结构突变)",
        host="httpbin.org",
        port=80,
        path="/get",
        expected_schema=broken_schema,
        email_receivers=["alert-admin@example.com", "backend-dev@example.com"]
    )


if __name__ == "__main__":
    asyncio.run(main())
