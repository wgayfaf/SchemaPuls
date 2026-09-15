import re
import time
import uuid
import random
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from app.services.template_engine import render_macro_string


def get_nested_value(data: Any, path: str) -> Tuple[bool, Any]:
    """
    通过点分或下标表达式提取嵌套数据
    例如: 'code', 'data.user.id', 'items[0].name', 'items.0.name'
    返回: (found: bool, value: Any)
    """
    if data is None or not path:
        return False, None

    # 标准化路径: 将 a[0].b 转为 a.0.b
    normalized = re.sub(r'\[(\d+)\]', r'.\1', path.strip())
    parts = [p for p in normalized.split('.') if p]

    curr = data
    for part in parts:
        if isinstance(curr, dict):
            if part in curr:
                curr = curr[part]
            else:
                return False, None
        elif isinstance(curr, (list, tuple)):
            try:
                idx = int(part)
                if 0 <= idx < len(curr):
                    curr = curr[idx]
                else:
                    return False, None
            except ValueError:
                return False, None
        else:
            return False, None

    return True, curr


def render_with_variables(text_val: Optional[str], variables: Dict[str, Any], auth_token: Optional[str] = None) -> Optional[str]:
    """结合上下文变量与内置宏对文本进行全面插值"""
    if text_val is None or not isinstance(text_val, str):
        return text_val

    # 1. 基础时间戳/UUID/随机数宏替换
    result = render_macro_string(text_val, auth_token=auth_token)

    # 2. 上下文变量插值: {{var_name}}
    if variables:
        for k, v in variables.items():
            pattern = f"{{{{{k}}}}}"
            if pattern in result:
                result = result.replace(pattern, str(v) if v is not None else "")

    return result


def execute_pre_actions(
    pre_actions: Optional[List[Dict[str, Any]]],
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    path: Optional[str] = None,
    auth_token: Optional[str] = None
) -> Tuple[Dict[str, str], Dict[str, str], Optional[str], Optional[str], Dict[str, Any]]:
    """
    执行前置操作列表
    返回: (final_headers, final_params, final_body, final_path, variables)
    """
    req_headers = dict(headers or {})
    req_params = dict(params or {})
    req_body = body
    req_path = path or ""
    variables: Dict[str, Any] = {}

    if auth_token:
        variables["TOKEN"] = auth_token

    if not pre_actions or not isinstance(pre_actions, list):
        return req_headers, req_params, req_body, req_path, variables

    for action in pre_actions:
        if not isinstance(action, dict) or not action.get("enabled", True):
            continue

        act_type = action.get("type", "").lower()
        key = str(action.get("key", "")).strip()
        raw_val = action.get("value", "")

        # 先用已知变量和内置宏计算当前值
        val_str = render_with_variables(str(raw_val), variables, auth_token=auth_token) if raw_val is not None else ""

        if act_type == "set_variable":
            if key:
                variables[key] = val_str
        elif act_type == "inject_header":
            if key:
                req_headers[key] = val_str
        elif act_type == "inject_param":
            if key:
                req_params[key] = val_str
        elif act_type == "custom_script":
            # 简易受限 Python 预请求脚本执行
            script_code = action.get("value", "") or action.get("script", "")
            if script_code and isinstance(script_code, str):
                local_scope = {
                    "variables": variables,
                    "headers": req_headers,
                    "params": req_params,
                    "body": req_body,
                    "path": req_path,
                    "time": time,
                    "uuid": uuid,
                    "random": random,
                    "json": json
                }
                try:
                    exec(script_code, {"__builtins__": {
                        "str": str, "int": int, "float": float, "bool": bool, "len": len,
                        "dict": dict, "list": list, "range": range, "round": round
                    }}, local_scope)
                    # 同步可能被脚本修改的值
                    if "body" in local_scope:
                        req_body = local_scope["body"]
                    if "path" in local_scope:
                        req_path = local_scope["path"]
                except Exception as e:
                    variables["_script_error"] = str(e)

    # 前置变量结算完毕后，对 headers, params, body, path 进行全面二次插值
    final_headers = {k: render_with_variables(v, variables, auth_token) for k, v in req_headers.items()}
    final_params = {k: render_with_variables(v, variables, auth_token) for k, v in req_params.items()}
    final_body = render_with_variables(req_body, variables, auth_token)
    final_path = render_with_variables(req_path, variables, auth_token)

    return final_headers, final_params, final_body, final_path, variables


def execute_post_actions(
    post_actions: Optional[List[Dict[str, Any]]],
    status_code: Optional[int],
    latency_ms: Optional[float],
    response_headers: Optional[Dict[str, str]] = None,
    response_data: Any = None,
    response_text: Optional[str] = None,
    context_variables: Optional[Dict[str, Any]] = None
) -> Tuple[bool, List[Dict[str, Any]], Dict[str, Any]]:
    """
    执行后置操作列表 (自动化断言校验与变量提取)
    返回: (all_passed: bool, assertions_result: List[Dict], extracted_variables: Dict)
    """
    assertions_result: List[Dict[str, Any]] = []
    extracted_vars: Dict[str, Any] = {}
    resp_headers = {k.lower(): v for k, v in (response_headers or {}).items()}

    # 预备文本供 contains 比对
    raw_text = response_text
    if raw_text is None and response_data is not None:
        try:
            raw_text = json.dumps(response_data, ensure_ascii=False)
        except Exception:
            raw_text = str(response_data)
    raw_text = raw_text or ""

    if not post_actions or not isinstance(post_actions, list):
        return True, assertions_result, extracted_vars

    for action in post_actions:
        if not isinstance(action, dict) or not action.get("enabled", True):
            continue

        act_type = action.get("type", "").lower()
        name = action.get("name") or action.get("description") or f"断言: {act_type}"
        op = (action.get("operator") or "equals").lower()
        target_val = action.get("target_value", "")
        expr = action.get("expression", "")

        # 变量替换期望值: 如期望值也是变量 {{expected_code}}
        if context_variables and isinstance(target_val, str):
            for vk, vv in context_variables.items():
                target_val = target_val.replace(f"{{{{{vk}}}}}", str(vv))

        passed = False
        actual_val = None
        message = ""

        # 1. 状态码断言
        if act_type == "assert_status_code":
            actual_val = status_code
            if status_code is None:
                passed = False
                message = "未收到 HTTP 响应状态码 (请求超时或连接失败)"
            elif op == "in_2xx":
                passed = (200 <= status_code < 300)
                message = f"实际状态码: {status_code} (期望: 2xx)"
            elif op == "not_equals":
                passed = (str(status_code) != str(target_val))
                message = f"实际状态码: {status_code} (期望不等于: {target_val})"
            else: # equals
                passed = (str(status_code) == str(target_val))
                message = f"实际状态码: {status_code} (期望: {target_val})"

            assertions_result.append({
                "name": name or f"HTTP 状态码等于 {target_val}",
                "type": act_type,
                "passed": passed,
                "actual": actual_val,
                "expected": target_val if op != "in_2xx" else "2xx",
                "operator": op,
                "message": message
            })

        # 2. 耗时断言
        elif act_type == "assert_latency":
            actual_val = latency_ms
            try:
                thresh = float(target_val)
                if latency_ms is None:
                    passed = False
                    message = "耗时未知 (请求未完成)"
                elif op == "greater_than":
                    passed = (latency_ms > thresh)
                    message = f"实际耗时: {latency_ms}ms (期望大于: {thresh}ms)"
                else: # less_than
                    passed = (latency_ms <= thresh)
                    message = f"实际耗时: {latency_ms}ms (期望小于: {thresh}ms)"
            except ValueError:
                passed = False
                message = f"耗时阈值非合法数字: {target_val}"

            assertions_result.append({
                "name": name or f"响应耗时小于 {target_val}ms",
                "type": act_type,
                "passed": passed,
                "actual": f"{actual_val}ms" if actual_val is not None else None,
                "expected": f"{target_val}ms",
                "operator": op,
                "message": message
            })

        # 3. JSONPath / 字段断言
        elif act_type == "assert_json_path":
            found, val = get_nested_value(response_data, expr)
            actual_val = val
            if not found:
                passed = (op == "not_exists")
                message = f"字段路径 '{expr}' 不存在于响应中" if not passed else f"字段路径 '{expr}' 预期不存在"
            else:
                if op == "not_empty":
                    passed = bool(val is not None and val != "" and val != [] and val != {})
                    message = f"字段 '{expr}' 当前值: {val} (非空校验)"
                elif op == "contains":
                    passed = (str(target_val) in str(val))
                    message = f"字段 '{expr}' 当前值: {val} (期望包含: {target_val})"
                elif op == "not_equals":
                    passed = (str(val) != str(target_val))
                    message = f"字段 '{expr}' 当前值: {val} (期望不等于: {target_val})"
                elif op == "type":
                    t_str = type(val).__name__
                    passed = (t_str.lower() == str(target_val).lower())
                    message = f"字段 '{expr}' 实际类型: {t_str} (期望: {target_val})"
                else: # equals
                    passed = (str(val) == str(target_val))
                    message = f"字段 '{expr}' 实际值: {val} (期望: {target_val})"

            assertions_result.append({
                "name": name or f"字段 [{expr}] 校验",
                "type": act_type,
                "expression": expr,
                "passed": passed,
                "actual": actual_val,
                "expected": target_val,
                "operator": op,
                "message": message
            })

        # 4. 响应头断言
        elif act_type == "assert_header":
            header_key = (expr or "").strip().lower()
            val = resp_headers.get(header_key)
            actual_val = val
            if val is None:
                passed = False
                message = f"响应头中未找到: {expr}"
            elif op == "contains":
                passed = (str(target_val).lower() in str(val).lower())
                message = f"响应头 '{expr}': {val} (期望包含: {target_val})"
            else:
                passed = (str(val).lower() == str(target_val).lower())
                message = f"响应头 '{expr}': {val} (期望: {target_val})"

            assertions_result.append({
                "name": name or f"响应头 [{expr}] 校验",
                "type": act_type,
                "expression": expr,
                "passed": passed,
                "actual": actual_val,
                "expected": target_val,
                "operator": op,
                "message": message
            })

        # 5. 响应文本包含断言
        elif act_type == "assert_body_contains":
            actual_val = raw_text[:200] + ("..." if len(raw_text) > 200 else "")
            if op == "not_contains":
                passed = (str(target_val) not in raw_text)
                message = f"响应文本已确认不包含: {target_val}" if passed else f"响应文本中包含敏感词: {target_val}"
            else:
                passed = (str(target_val) in raw_text)
                message = f"响应文本成功包含: {target_val}" if passed else f"响应文本未找到: {target_val}"

            assertions_result.append({
                "name": name or f"响应内容包含 [{target_val}]",
                "type": act_type,
                "passed": passed,
                "actual": actual_val,
                "expected": target_val,
                "operator": op,
                "message": message
            })

        # 6. 响应变量提取
        elif act_type == "extract_variable":
            var_name = (action.get("target_value") or action.get("key") or "extracted_var").strip()
            found, val = get_nested_value(response_data, expr)
            if found:
                extracted_vars[var_name] = val
                assertions_result.append({
                    "name": name or f"提取变量 [{var_name}]",
                    "type": act_type,
                    "expression": expr,
                    "passed": True,
                    "actual": val,
                    "expected": var_name,
                    "operator": "extract",
                    "message": f"成功提取变量 {var_name} = {val}"
                })
            else:
                # 尝试从响应头提取
                h_val = resp_headers.get(expr.strip().lower())
                if h_val is not None:
                    extracted_vars[var_name] = h_val
                    assertions_result.append({
                        "name": name or f"提取Header变量 [{var_name}]",
                        "type": act_type,
                        "expression": expr,
                        "passed": True,
                        "actual": h_val,
                        "expected": var_name,
                        "operator": "extract",
                        "message": f"成功提取Header变量 {var_name} = {h_val}"
                    })
                else:
                    assertions_result.append({
                        "name": name or f"提取变量 [{var_name}]",
                        "type": act_type,
                        "expression": expr,
                        "passed": False,
                        "actual": None,
                        "expected": var_name,
                        "operator": "extract",
                        "message": f"未在响应数据或响应头中找到 '{expr}'"
                    })

    # 判定全部断言是否通过 (忽略 extract_variable)
    pure_assertions = [a for a in assertions_result if a.get("type") != "extract_variable"]
    all_passed = all(a["passed"] for a in pure_assertions) if pure_assertions else True

    return all_passed, assertions_result, extracted_vars
