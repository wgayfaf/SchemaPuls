import re
import time
import uuid
import random
from typing import Any, Dict, List, Optional, Union, Tuple


def render_macro_string(template: str, auth_token: Optional[str] = None) -> str:
    """对字符串中的动态宏变量进行插值替换"""
    if not template or not isinstance(template, str):
        return template

    now = time.time()

    # 1. 内置时间戳宏
    res = template.replace("{{$timestamp}}", str(int(now)))
    res = res.replace("{{$timestamp_ms}}", str(int(now * 1000)))

    # 2. 内置 UUID 宏
    if "{{$uuid}}" in res:
        while "{{$uuid}}" in res:
            res = res.replace("{{$uuid}}", str(uuid.uuid4()), 1)

    # 3. 随机数宏: {{$randomInt(1, 100)}}
    random_int_pattern = re.compile(r"\{\{\$randomInt\((\d+),\s*(\d+)\)\}\}")
    for match in random_int_pattern.finditer(res):
        full_match = match.group(0)
        min_val = int(match.group(1))
        max_val = int(match.group(2))
        res = res.replace(full_match, str(random.randint(min_val, max_val)), 1)

    # 4. Token 变量替换
    if auth_token:
        res = res.replace("{{TOKEN}}", auth_token)
        res = res.replace("{{$env.TOKEN}}", auth_token)

    return res


def render_template_value(val: Any, auth_token: Optional[str] = None) -> Any:
    """递归替换各类数据结构中的模板宏"""
    if isinstance(val, str):
        return render_macro_string(val, auth_token)
    elif isinstance(val, dict):
        return {k: render_template_value(v, auth_token) for k, v in val.items()}
    elif isinstance(val, list):
        return [render_template_value(item, auth_token) for item in val]
    return val


def parse_params_to_dict(params_list: List[Dict[str, Any]], auth_token: Optional[str] = None) -> Dict[str, str]:
    """将前端 Params 动态列表格式转为 requests/httpx 所需的键值对字典 (仅保留勾选启用的项)"""
    result = {}
    if not params_list or not isinstance(params_list, list):
        return result
        
    for item in params_list:
        if isinstance(item, dict) and item.get("enabled", True):
            key = str(item.get("key", "")).strip()
            if key:
                val = str(item.get("value", ""))
                result[key] = render_macro_string(val, auth_token)
    return result


def parse_headers_to_dict(headers_data: Union[Dict[str, str], List[Dict[str, Any]]], auth_token: Optional[str] = None) -> Dict[str, str]:
    """将 Header 字典或列表转为规范化的请求头字典"""
    result = {}
    if not headers_data:
        return result

    if isinstance(headers_data, list):
        for item in headers_data:
            if isinstance(item, dict) and item.get("enabled", True):
                key = str(item.get("key", "")).strip()
                if key:
                    val = str(item.get("value", ""))
                    result[key] = render_macro_string(val, auth_token)
    elif isinstance(headers_data, dict):
        for k, v in headers_data.items():
            if k:
                result[str(k)] = render_macro_string(str(v), auth_token)

    return result


def resolve_path_variables(
    path: str,
    params_dict: Optional[Dict[str, str]] = None,
    variables: Optional[Dict[str, Any]] = None
) -> Tuple[str, Dict[str, str]]:
    """
    解析并替换路径参数 (Path Variables, 如 /detail/{tableId} 或 /detail/:tableId)
    支持从 params_dict 及全局 variables (环境变量/上下文) 中提取对应键值进行原地插值替换。
    将已用于路径替换的 params 剔除，返回 (resolved_path, remaining_query_params)
    """
    if not path:
        return path or "", dict(params_dict or {})
        
    resolved_path = path
    remaining_params = dict(params_dict or {})
    
    # 1. 优先使用 params_dict 替换路径参数
    if params_dict:
        for k, v in params_dict.items():
            if not k:
                continue
            k_str = str(k).strip()
            curly_pattern = r'\{\s*' + re.escape(k_str) + r'\s*\}'
            colon_pattern = r':' + re.escape(k_str) + r'\b'
            
            replaced = False
            if re.search(curly_pattern, resolved_path):
                resolved_path = re.sub(curly_pattern, str(v) if v is not None else "", resolved_path)
                replaced = True
            elif re.search(colon_pattern, resolved_path):
                resolved_path = re.sub(colon_pattern, str(v) if v is not None else "", resolved_path)
                replaced = True
                
            if replaced:
                remaining_params.pop(k, None)
                
    # 2. 如果还有未替换的路径变量，尝试从 variables (环境变量/前置脚本变量) 中查找
    if variables:
        for k, v in variables.items():
            if not k or str(k).startswith("_"):
                continue
            k_str = str(k).strip()
            curly_pattern = r'\{\s*' + re.escape(k_str) + r'\s*\}'
            colon_pattern = r':' + re.escape(k_str) + r'\b'
            if re.search(curly_pattern, resolved_path):
                resolved_path = re.sub(curly_pattern, str(v) if v is not None else "", resolved_path)
            elif re.search(colon_pattern, resolved_path):
                resolved_path = re.sub(colon_pattern, str(v) if v is not None else "", resolved_path)
                
    return resolved_path, remaining_params


