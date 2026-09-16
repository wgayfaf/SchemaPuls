import io
import re
import json
import zipfile
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
from sqlmodel import Session, select
from app.models import MachineNode, ServiceGroup, Environment, ApiProbe
from app.services.scheduler import add_api_job

def _decode_bytes(b: bytes) -> str:
    """尝试多种编码解码字节流"""
    for enc in ['utf-8', 'utf-8-sig', 'gbk', 'cp1252', 'latin1']:
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode('utf-8', errors='ignore')

def _clean_relative_path(raw_url: str, machine_base_url: Optional[str] = None) -> str:
    """
    智能剥离 URL 前缀，转换为标准相对路径:
    1. 剥离 {{baseUrl}}、{{base_url}}、{{HOST}} 等环境占位符
    2. 若以 http(s):// 开头，且与 machine_base_url 匹配，则剥离该前缀
    3. 否则提取 urlparse 的 pathname + search
    """
    if not raw_url:
        return ""
    
    url = raw_url.strip()
    
    # 1. 剥离 {{baseUrl}} 宏前缀
    url = re.sub(r'^\{\{\s*(baseUrl|base_url|host|HOST|BASE_URL)\s*\}\}', '', url, flags=re.IGNORECASE)
    
    # 2. 若仍然以 http:// 或 https:// 开头
    if url.startswith("http://") or url.startswith("https://"):
        if machine_base_url and url.startswith(machine_base_url.strip()):
            url = url[len(machine_base_url.strip()):]
        else:
            try:
                parsed = urlparse(url)
                path = parsed.path or "/"
                if parsed.query:
                    path = f"{path}?{parsed.query}"
                url = path
            except Exception:
                pass
                
    # 确保以 / 开头（如果是相对路径）
    if url and not url.startswith("/") and not url.startswith("?"):
        url = "/" + url
        
    return url

def _parse_postman_script(script_obj: Any) -> str:
    """提取 postman 脚本中的执行文本 (数组或字符串)"""
    if not script_obj:
        return ""
    exec_content = script_obj.get("exec", "")
    if isinstance(exec_content, list):
        # Postman 导出的 exec 为每行一字符串
        return "\n".join(exec_content)
    elif isinstance(exec_content, str):
        return exec_content
    return ""

def _extract_requests_from_items(items: List[Dict[str, Any]], folder_prefix: str = "", machine_base_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """递归提取 Postman item 树下的所有 HTTP requests"""
    extracted_apis = []
    
    for it in items:
        name = (it.get("name") or "").strip()
        full_name = f"{folder_prefix} / {name}" if folder_prefix else name
        
        # 1. 如果包含子 item 列表，代表是文件夹/分组，递归处理
        if "item" in it and isinstance(it["item"], list):
            extracted_apis.extend(_extract_requests_from_items(it["item"], full_name, machine_base_url))
        
        # 2. 如果包含 request，代表是具体接口
        elif "request" in it and isinstance(it["request"], dict):
            req = it["request"]
            method = (req.get("method") or "GET").upper()
            
            # 解析 URL
            url_obj = req.get("url", {})
            raw_url = ""
            query_list = []
            
            if isinstance(url_obj, str):
                raw_url = url_obj
            elif isinstance(url_obj, dict):
                raw_url = url_obj.get("raw", "")
                for q in url_obj.get("query", []):
                    if isinstance(q, dict) and q.get("key"):
                        query_list.append({
                            "enabled": not q.get("disabled", False),
                            "key": str(q.get("key", "")),
                            "value": str(q.get("value", "")),
                            "description": str(q.get("description", ""))
                        })
            
            # 清理出相对路径
            http_path = _clean_relative_path(raw_url, machine_base_url)
            
            # 解析 Headers
            headers_list = []
            for h in req.get("header", []):
                if isinstance(h, dict) and h.get("key"):
                    headers_list.append({
                        "enabled": not h.get("disabled", False),
                        "key": str(h.get("key", "")),
                        "value": str(h.get("value", "")),
                        "description": str(h.get("description", ""))
                    })
            
            # 解析 Body
            body_obj = req.get("body", {})
            http_body_type = "none"
            http_body = ""
            
            if isinstance(body_obj, dict):
                mode = body_obj.get("mode")
                if mode == "raw":
                    raw_text = body_obj.get("raw", "")
                    http_body = raw_text
                    # 检查是否为 JSON 格式
                    opts = body_obj.get("options", {}).get("raw", {})
                    lang = opts.get("language", "") if isinstance(opts, dict) else ""
                    if lang == "json" or (raw_text.strip().startswith("{") and raw_text.strip().endswith("}")):
                        http_body_type = "json"
                    else:
                        http_body_type = "raw"
                elif mode == "urlencoded":
                    http_body_type = "form"
                    pairs = []
                    for item in body_obj.get("urlencoded", []):
                        if isinstance(item, dict) and not item.get("disabled", False):
                            pairs.append(f"{item.get('key', '')}={item.get('value', '')}")
                    http_body = "&".join(pairs)
            
            # 解析 Pre-request 与 Test 脚本事件
            pre_actions = []
            post_actions = []
            
            for event in it.get("event", []):
                if not isinstance(event, dict):
                    continue
                listen = event.get("listen")
                script = event.get("script", {})
                script_code = _parse_postman_script(script).strip()
                
                if not script_code:
                    continue
                    
                if listen == "prerequest":
                    pre_actions.append({
                        "enabled": True,
                        "type": "javascript",
                        "key": "",
                        "value": script_code,
                        "description": "Postman Pre-request 脚本"
                    })
                elif listen == "test":
                    post_actions.append({
                        "enabled": True,
                        "name": "Postman JS 测试断言",
                        "type": "javascript",
                        "expression": "",
                        "operator": "pm.test",
                        "target_value": "",
                        "value": script_code,
                        "description": "Postman Tests 测试脚本"
                    })
            
            extracted_apis.append({
                "name": full_name or "未命名接口",
                "http_method": method,
                "raw_url": raw_url,
                "http_path": http_path,
                "http_params": query_list,
                "http_headers": headers_list,
                "http_body_type": http_body_type,
                "http_body": http_body,
                "pre_actions": pre_actions,
                "post_actions": post_actions,
                "expected_schema": {}
            })
            
    return extracted_apis

def parse_postman_package(file_bytes: bytes, filename: str = "", machine_base_url: Optional[str] = None) -> Dict[str, Any]:
    """
    智能解析上传的 Postman 数据文件 (支持 .zip 或 .json 或 JSON 字符串):
    返回:
    {
        "collection_name": str,
        "base_url": str | None,
        "environment_name": str | None,
        "environment_variables": Dict[str, Any],
        "apis": List[Dict[str, Any]]
    }
    """
    result = {
        "collection_name": "",
        "base_url": None,
        "environment_name": None,
        "environment_variables": {},
        "apis": []
    }
    
    # 1. 判断是否为 ZIP 压缩包
    if filename.lower().endswith(".zip") or file_bytes.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                for zinfo in z.infolist():
                    fname = zinfo.filename
                    # 兼容中文文件名解码
                    try:
                        fname = zinfo.filename.encode('cp437').decode('utf-8')
                    except Exception:
                        try:
                            fname = zinfo.filename.encode('cp437').decode('gbk')
                        except Exception:
                            fname = zinfo.filename
                            
                    if fname.startswith("__MACOSX/") or not fname.lower().endswith(".json"):
                        continue
                        
                    content_str = _decode_bytes(z.read(zinfo.filename))
                    try:
                        doc = json.loads(content_str)
                        # 识别环境文件
                        if doc.get("_postman_variable_scope") == "environment" or ("values" in doc and isinstance(doc.get("values"), list)):
                            result["environment_name"] = doc.get("name", "Postman环境")
                            for v in doc.get("values", []):
                                if isinstance(v, dict) and v.get("key") and v.get("enabled", True):
                                    k = str(v["key"]).strip()
                                    val = str(v.get("value", ""))
                                    if k.lower() in ["baseurl", "base_url"]:
                                        result["base_url"] = val
                                    result["environment_variables"][k] = val
                        # 识别集合文件
                        elif "info" in doc and "item" in doc:
                            result["collection_name"] = doc.get("info", {}).get("name", "Postman集合")
                            effective_base = result["base_url"] or machine_base_url
                            apis = _extract_requests_from_items(doc.get("item", []), "", effective_base)
                            result["apis"].extend(apis)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise ValueError(f"无法解压并解析 Postman ZIP 压缩包: {str(e)}")
            
    # 2. 单个 JSON 文件或文本
    else:
        content_str = _decode_bytes(file_bytes)
        try:
            doc = json.loads(content_str)
            if doc.get("_postman_variable_scope") == "environment" or ("values" in doc and isinstance(doc.get("values"), list)):
                result["environment_name"] = doc.get("name", "Postman环境")
                for v in doc.get("values", []):
                    if isinstance(v, dict) and v.get("key") and v.get("enabled", True):
                        k = str(v["key"]).strip()
                        val = str(v.get("value", ""))
                        if k.lower() in ["baseurl", "base_url"]:
                            result["base_url"] = val
                        result["environment_variables"][k] = val
            elif "info" in doc and "item" in doc:
                result["collection_name"] = doc.get("info", {}).get("name", "Postman集合")
                apis = _extract_requests_from_items(doc.get("item", []), "", machine_base_url)
                result["apis"].extend(apis)
            else:
                raise ValueError("未检测到标准的 Postman Collection (集合) 或 Environment (环境) 结构")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 格式解析失败: {str(e)}")
            
    return result

def import_postman_to_machine(
    db: Session,
    machine_id: int,
    selected_apis: List[Dict[str, Any]],
    environment_variables: Dict[str, Any] = {},
    postman_base_url: Optional[str] = None,
    sync_env_vars: bool = True,
    update_machine_base_url: bool = True,
    conflict_policy: str = "rename", # rename | overwrite | skip
    cron_interval_minutes: int = 5
) -> Dict[str, Any]:
    """
    将选中的 Postman 接口批量持久化关联到指定机器节点，并同步环境与调度
    """
    # 1. 查询机器与环境
    machine = db.get(MachineNode, machine_id)
    if not machine:
        raise ValueError(f"目标机器节点不存在 (ID: {machine_id})")
        
    group = db.get(ServiceGroup, machine.group_id)
    env = db.get(Environment, group.environment_id) if group else None
    
    # 2. 如果包含 baseUrl 且机器未设置或允许更新，同步更新机器的 base_url
    updated_machine_base_url = False
    if postman_base_url and update_machine_base_url:
        if not machine.base_url or not machine.base_url.strip():
            machine.base_url = postman_base_url.strip()
            db.add(machine)
            updated_machine_base_url = True
            
    # 3. 同步环境变量到该机器所属环境
    updated_env_count = 0
    if sync_env_vars and env and environment_variables:
        current_vars = env.variables or {}
        for k, v in environment_variables.items():
            current_vars[k] = v
        env.variables = current_vars
        db.add(env)
        updated_env_count = len(environment_variables)
        
    db.commit()
    db.refresh(machine)
    if env:
        db.refresh(env)
        
    # 4. 批量保存接口探针
    created_count = 0
    overwritten_count = 0
    skipped_count = 0
    created_ids = []
    
    for api_data in selected_apis:
        api_name = (api_data.get("name") or "未命名接口").strip()
        http_method = (api_data.get("http_method") or "GET").upper()
        http_path = (api_data.get("http_path") or "/").strip()
        
        # 检查是否已有同名接口隶属于该机器
        existing_stmt = select(ApiProbe).where(
            ApiProbe.machine_id == machine_id,
            ApiProbe.name == api_name
        )
        existing_probe = db.exec(existing_stmt).first()
        
        target_probe = None
        if existing_probe:
            if conflict_policy == "skip":
                skipped_count += 1
                continue
            elif conflict_policy == "overwrite":
                target_probe = existing_probe
                overwritten_count += 1
            else: # rename
                # 累加副本后缀
                copy_idx = 1
                new_name = f"{api_name} (副本)"
                while db.exec(select(ApiProbe).where(ApiProbe.machine_id == machine_id, ApiProbe.name == new_name)).first():
                    copy_idx += 1
                    new_name = f"{api_name} (副本{copy_idx})"
                api_name = new_name
                target_probe = ApiProbe(machine_id=machine_id, name=api_name)
                created_count += 1
        else:
            target_probe = ApiProbe(machine_id=machine_id, name=api_name)
            created_count += 1
            
        # 填充属性
        target_probe.http_method = http_method
        target_probe.http_path = http_path
        target_probe.base_url = None # 默认继承机器 base_url
        target_probe.http_params = api_data.get("http_params", [])
        target_probe.http_headers = api_data.get("http_headers", [])
        target_probe.http_body_type = api_data.get("http_body_type", "none")
        target_probe.http_body = api_data.get("http_body", "")
        target_probe.pre_actions = api_data.get("pre_actions", [])
        target_probe.post_actions = api_data.get("post_actions", [])
        target_probe.expected_schema = api_data.get("expected_schema", {})
        target_probe.cron_interval_minutes = cron_interval_minutes
        target_probe.is_active = True
        
        db.add(target_probe)
        db.commit()
        db.refresh(target_probe)
        
        # 热加载注册到后台定时探活调度器
        try:
            add_api_job(target_probe)
        except Exception:
            pass
            
        created_ids.append(target_probe.id)
        
    return {
        "machine_id": machine.id,
        "machine_name": machine.name,
        "machine_base_url": machine.base_url,
        "environment_name": env.name if env else None,
        "updated_machine_base_url": updated_machine_base_url,
        "synced_env_vars_count": updated_env_count,
        "total_imported": created_count + overwritten_count,
        "created_count": created_count,
        "overwritten_count": overwritten_count,
        "skipped_count": skipped_count,
        "created_ids": created_ids
    }
