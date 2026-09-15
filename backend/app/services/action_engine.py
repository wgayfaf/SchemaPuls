import os
import re
import time
import uuid
import random
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from app.services.template_engine import render_macro_string

JS_LIBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "js_libs")
_CACHED_JSRSASIGN: Optional[str] = None
_CACHED_CRYPTOJS: Optional[str] = None


def get_jsrsasign_code() -> str:
    global _CACHED_JSRSASIGN
    if _CACHED_JSRSASIGN is None:
        p = os.path.join(JS_LIBS_DIR, "jsrsasign.min.js")
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    _CACHED_JSRSASIGN = f.read()
            except Exception:
                _CACHED_JSRSASIGN = ""
        else:
            _CACHED_JSRSASIGN = ""
    return _CACHED_JSRSASIGN


def get_cryptojs_code() -> str:
    global _CACHED_CRYPTOJS
    if _CACHED_CRYPTOJS is None:
        p = os.path.join(JS_LIBS_DIR, "crypto-js.min.js")
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    _CACHED_CRYPTOJS = f.read()
            except Exception:
                _CACHED_CRYPTOJS = ""
        else:
            _CACHED_CRYPTOJS = ""
    return _CACHED_CRYPTOJS


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


def setup_quickjs_runtime(ctx: Any, script_code: str):
    """
    为 QuickJS 沙箱注入标准环境 polyfill（btoa, atob, Buffer, require）
    并在脚本需要时动态装载 jsrsasign (含 KEYUTIL, KJUR, CryptoJS, ASN1HEX, X509) 与 crypto-js
    """
    base_js = """
    var window = globalThis;
    var navigator = { userAgent: "SchemaPulse/QuickJS" };
    var _b64chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=';
    function btoa(input) {
        var str = String(input);
        var output = '';
        for (var block = 0, charCode, i = 0, map = _b64chars;
             str.charAt(i | 0) || (map = '=', i % 1);
             output += map.charAt(63 & block >> 8 - i % 1 * 8)) {
            charCode = str.charCodeAt(i += 3/4);
            if (charCode > 0xFF) {
                throw new Error("'btoa' failed: The string to be encoded contains characters outside of the Latin1 range.");
            }
            block = block << 8 | charCode;
        }
        return output;
    }
    function atob(input) {
        var str = String(input).replace(/[=]+$/, '');
        var output = '';
        for (var bc = 0, bs = 0, buffer, i = 0;
             buffer = str.charAt(i++);
             ~buffer && (bs = bc % 4 ? bs * 64 + buffer : buffer,
               bc++ % 4) ? output += String.fromCharCode(255 & bs >> (-2 * bc & 6)) : 0
        ) {
            buffer = _b64chars.indexOf(buffer);
        }
        return output;
    }

    var Buffer = {
        from: function(data, enc) {
            var bytes;
            if (data instanceof Uint8Array || Array.isArray(data)) {
                bytes = data;
            } else if (typeof data === 'string') {
                if (enc === 'hex') {
                    bytes = [];
                    for (var i = 0; i < data.length; i += 2) bytes.push(parseInt(data.substr(i, 2), 16));
                } else if (enc === 'base64') {
                    var bin = atob(data);
                    bytes = [];
                    for (var i = 0; i < bin.length; i++) bytes.push(bin.charCodeAt(i));
                } else {
                    bytes = [];
                    for (var i = 0; i < data.length; i++) bytes.push(data.charCodeAt(i));
                }
            } else {
                bytes = [];
            }
            return {
                toString: function(outEnc) {
                    if (outEnc === 'base64') {
                        var bin = '';
                        for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
                        return btoa(bin);
                    }
                    if (outEnc === 'hex') {
                        var hex = '';
                        for (var i = 0; i < bytes.length; i++) {
                            var h = (bytes[i] & 0xFF).toString(16);
                            hex += (h.length === 1 ? '0' : '') + h;
                        }
                        return hex;
                    }
                    var s = '';
                    for (var i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
                    return s;
                }
            };
        }
    };
    """
    ctx.eval(base_js)

    # 检查是否需要密码学库
    needs_jsrsasign = any(k in script_code for k in ["jsrsasign", "KEYUTIL", "KJUR", "ASN1HEX", "X509"])
    needs_cryptojs = any(k in script_code for k in ["crypto-js", "CryptoJS", "crypto"])

    if needs_jsrsasign:
        code = get_jsrsasign_code()
        if code:
            ctx.eval(code)
    elif needs_cryptojs:
        code = get_cryptojs_code()
        if code:
            ctx.eval(code)

    wire_require_js = """
    var jsrsasignObj = (typeof globalThis.KEYUTIL !== 'undefined') ? {
        KEYUTIL: globalThis.KEYUTIL,
        KJUR: globalThis.KJUR,
        CryptoJS: globalThis.CryptoJS || {},
        ASN1HEX: globalThis.ASN1HEX || {},
        X509: globalThis.X509 || {}
    } : null;

    if (jsrsasignObj) {
        globalThis.jsrsasign = jsrsasignObj;
    }

    function require(moduleName) {
        var name = String(moduleName).toLowerCase().trim();
        if (name === 'jsrsasign') {
            if (jsrsasignObj) return jsrsasignObj;
            if (globalThis.jsrsasign) return globalThis.jsrsasign;
            throw new Error("Cannot find module 'jsrsasign'. 请确认内置 jsrsasign 库已就绪");
        }
        if (name === 'crypto-js') {
            if (globalThis.CryptoJS) return globalThis.CryptoJS;
            throw new Error("Cannot find module 'crypto-js'");
        }
        if (name === 'buffer') {
            return { Buffer: globalThis.Buffer || Buffer };
        }
        throw new Error("Cannot find module '" + moduleName + "'. 内置支持模块: ['jsrsasign', 'crypto-js', 'buffer']");
    }
    """
    ctx.eval(wire_require_js)


def run_quickjs_pre_script(
    script_code: str,
    variables: Dict[str, Any],
    headers: Dict[str, str],
    params: Dict[str, str],
    path: str,
    body: Optional[str]
) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, str], str, Optional[str], Optional[str]]:
    """
    使用 QuickJS 执行 Postman 风格 JavaScript 预请求脚本 (ES2020+)
    返回: (variables, headers, params, path, body, error_message)
    """
    try:
        import quickjs
    except ImportError:
        return variables, headers, params, path, body, "QuickJS 运行时未安装，请执行 pip install quickjs"

    try:
        ctx = quickjs.Context()
        ctx.set_time_limit(2.0)  # 2秒超时保护
        ctx.set_memory_limit(30 * 1024 * 1024)  # 30MB 内存保护

        # 注入标准 Polyfill 及 require、jsrsasign、crypto-js 支持
        setup_quickjs_runtime(ctx, script_code)

        setup_js = f"""
        var variables = {json.dumps(variables, ensure_ascii=False)};
        var headers = {json.dumps(headers, ensure_ascii=False)};
        var params = {json.dumps(params, ensure_ascii=False)};
        var request = {{
            path: {json.dumps(path, ensure_ascii=False)},
            body: {json.dumps(body, ensure_ascii=False)}
        }};
        var _console_logs = [];
        var console = {{
            log: function() {{ _console_logs.push(Array.prototype.slice.call(arguments).map(String).join(' ')); }},
            warn: function() {{ _console_logs.push('[WARN] ' + Array.prototype.slice.call(arguments).map(String).join(' ')); }},
            error: function() {{ _console_logs.push('[ERROR] ' + Array.prototype.slice.call(arguments).map(String).join(' ')); }},
            info: function() {{ _console_logs.push('[INFO] ' + Array.prototype.slice.call(arguments).map(String).join(' ')); }}
        }};
        var pm = {{
            variables: {{
                set: function(k, v) {{ variables[String(k)] = (v !== undefined && v !== null) ? v : ""; }},
                get: function(k) {{ return variables[String(k)]; }}
            }},
            environment: {{
                set: function(k, v) {{ variables[String(k)] = (v !== undefined && v !== null) ? v : ""; }},
                get: function(k) {{ return variables[String(k)]; }}
            }},
            globals: {{
                set: function(k, v) {{ variables[String(k)] = (v !== undefined && v !== null) ? v : ""; }},
                get: function(k) {{ return variables[String(k)]; }}
            }},
            collectionVariables: {{
                set: function(k, v) {{ variables[String(k)] = (v !== undefined && v !== null) ? v : ""; }},
                get: function(k) {{ return variables[String(k)]; }}
            }},
            request: {{
                headers: {{
                    add: function(obj) {{
                        if (typeof obj === 'string') {{
                            var p = obj.indexOf(':');
                            if (p > -1) headers[obj.substring(0, p).trim()] = obj.substring(p + 1).trim();
                        }} else if (obj && obj.key) {{
                            headers[String(obj.key)] = (obj.value !== undefined && obj.value !== null) ? String(obj.value) : "";
                        }}
                    }},
                    upsert: function(obj) {{
                        if (obj && obj.key) {{
                            headers[String(obj.key)] = (obj.value !== undefined && obj.value !== null) ? String(obj.value) : "";
                        }}
                    }},
                    get: function(k) {{ return headers[String(k)]; }},
                    remove: function(k) {{ delete headers[String(k)]; }}
                }},
                addHeader: function(strOrObj) {{
                    if (typeof strOrObj === 'string') {{
                        var p = strOrObj.indexOf(':');
                        if (p > -1) headers[strOrObj.substring(0, p).trim()] = strOrObj.substring(p + 1).trim();
                    }} else if (strOrObj && strOrObj.key) {{
                        headers[String(strOrObj.key)] = (strOrObj.value !== undefined && strOrObj.value !== null) ? String(strOrObj.value) : "";
                    }}
                }},
                url: {{
                    query: {{
                        add: function(strOrObj) {{
                            if (typeof strOrObj === 'string') {{
                                var p = strOrObj.indexOf('=');
                                if (p > -1) params[strOrObj.substring(0, p).trim()] = strOrObj.substring(p + 1).trim();
                            }} else if (strOrObj && strOrObj.key) {{
                                params[String(strOrObj.key)] = (strOrObj.value !== undefined && strOrObj.value !== null) ? String(strOrObj.value) : "";
                            }}
                        }}
                    }}
                }},
                body: {{
                    get raw() {{ return request.body; }},
                    set raw(val) {{ request.body = (typeof val === 'string') ? val : JSON.stringify(val); }},
                    update: function(newBody) {{
                        request.body = (typeof newBody === 'string') ? newBody : JSON.stringify(newBody);
                    }}
                }}
            }}
        }};
        """
        ctx.eval(setup_js)
        ctx.eval(script_code)

        result_raw = ctx.eval("JSON.stringify({ variables: variables, headers: headers, params: params, request: request, logs: _console_logs })")
        res_dict = json.loads(result_raw)

        new_vars = dict(res_dict.get("variables") or {})
        logs = res_dict.get("logs") or []
        if logs:
            new_vars["_console_logs"] = logs

        new_headers = {str(k): str(v) for k, v in (res_dict.get("headers") or {}).items()}
        new_params = {str(k): str(v) for k, v in (res_dict.get("params") or {}).items()}
        req_obj = res_dict.get("request") or {}
        new_path = str(req_obj.get("path") or path)
        new_body = req_obj.get("body")
        if new_body is not None and not isinstance(new_body, str):
            new_body = json.dumps(new_body, ensure_ascii=False)
        return new_vars, new_headers, new_params, new_path, new_body, None
    except Exception as e:
        return variables, headers, params, path, body, str(e)


def run_quickjs_post_script(
    script_code: str,
    status_code: Optional[int],
    latency_ms: Optional[float],
    response_data: Any,
    response_text: Optional[str],
    response_headers: Dict[str, str],
    context_variables: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Optional[str]]:
    """
    使用 QuickJS 执行 Postman Tests 风格 JavaScript 测试脚本 (ES2020+)
    返回: (assertions_result, extracted_vars, error_message)
    """
    try:
        import quickjs
    except ImportError:
        return [], {}, "QuickJS 运行时未安装，请执行 pip install quickjs"

    try:
        ctx = quickjs.Context()
        ctx.set_time_limit(2.0)
        ctx.set_memory_limit(30 * 1024 * 1024)

        # 注入标准 Polyfill 及 require、jsrsasign、crypto-js 支持
        setup_quickjs_runtime(ctx, script_code)

        setup_js = f"""
        var status_code = {json.dumps(status_code)};
        var latency_ms = {json.dumps(latency_ms)};
        var response_data = {json.dumps(response_data, ensure_ascii=False)};
        var response_text = {json.dumps(response_text or "", ensure_ascii=False)};
        var resp_headers = {json.dumps(response_headers, ensure_ascii=False)};
        var context_variables = {json.dumps(context_variables, ensure_ascii=False)};
        var extracted_vars = {{}};
        var assertions = [];
        var _console_logs = [];
        var console = {{
            log: function() {{ _console_logs.push(Array.prototype.slice.call(arguments).map(String).join(' ')); }},
            warn: function() {{ _console_logs.push('[WARN] ' + Array.prototype.slice.call(arguments).map(String).join(' ')); }},
            error: function() {{ _console_logs.push('[ERROR] ' + Array.prototype.slice.call(arguments).map(String).join(' ')); }},
            info: function() {{ _console_logs.push('[INFO] ' + Array.prototype.slice.call(arguments).map(String).join(' ')); }}
        }};

        var pm = {{
            test: function(name, fn) {{
                try {{
                    fn();
                    assertions.push({{ name: String(name), passed: true, message: "断言校验通过" }});
                }} catch (e) {{
                    assertions.push({{ name: String(name), passed: false, message: e.message || String(e) }});
                }}
            }},
            expect: function(actual) {{
                return {{
                    to: {{
                        equal: function(expected) {{
                            if (actual != expected) throw new Error("期望等于 " + JSON.stringify(expected) + "，但实际为 " + JSON.stringify(actual));
                        }},
                        eql: function(expected) {{
                            if (JSON.stringify(actual) != JSON.stringify(expected)) throw new Error("期望 eql " + JSON.stringify(expected) + "，但实际为 " + JSON.stringify(actual));
                        }},
                        have: {{
                            status: function(expected) {{
                                if (status_code != expected) throw new Error("期望状态码 " + expected + "，但实际为 " + status_code);
                            }}
                        }},
                        be: {{
                            above: function(val) {{
                                if (!(actual > val)) throw new Error("期望大于 " + val + "，但实际为 " + actual);
                            }},
                            below: function(val) {{
                                if (!(actual < val)) throw new Error("期望小于 " + val + "，但实际为 " + actual);
                            }},
                            true: function() {{
                                if (actual !== true) throw new Error("期望为 true，但实际为 " + actual);
                            }},
                            false: function() {{
                                if (actual !== false) throw new Error("期望为 false，但实际为 " + actual);
                            }}
                        }},
                        include: function(item) {{
                            if (typeof actual === 'string') {{
                                if (actual.indexOf(item) === -1) throw new Error("期望包含 " + JSON.stringify(item));
                            }} else if (Array.isArray(actual)) {{
                                if (actual.indexOf(item) === -1) throw new Error("期望数组包含 " + JSON.stringify(item));
                            }}
                        }}
                    }}
                }};
            }},
            response: {{
                code: status_code,
                status: status_code,
                responseTime: latency_ms,
                json: function() {{ return response_data; }},
                text: function() {{ return response_text; }},
                headers: {{
                    get: function(k) {{ return resp_headers[String(k).toLowerCase()]; }}
                }},
                to: {{
                    have: {{
                        status: function(exp) {{
                            if (status_code != exp) throw new Error("期望状态码 " + exp + "，实际为 " + status_code);
                        }}
                    }}
                }}
            }},
            variables: {{
                set: function(k, v) {{ extracted_vars[String(k)] = v; }},
                get: function(k) {{ return extracted_vars[String(k)] !== undefined ? extracted_vars[String(k)] : context_variables[String(k)]; }}
            }},
            environment: {{
                set: function(k, v) {{ extracted_vars[String(k)] = v; }},
                get: function(k) {{ return extracted_vars[String(k)] !== undefined ? extracted_vars[String(k)] : context_variables[String(k)]; }}
            }}
        }};
        """
        ctx.eval(setup_js)
        ctx.eval(script_code)

        result_raw = ctx.eval("JSON.stringify({ assertions: assertions, extracted_vars: extracted_vars, logs: _console_logs })")
        res_dict = json.loads(result_raw)
        extracted = res_dict.get("extracted_vars", {})
        logs = res_dict.get("logs") or []
        if logs:
            extracted["_console_logs"] = logs
        return res_dict.get("assertions", []), extracted, None
    except Exception as e:
        return [], {}, str(e)



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
        elif act_type in ["javascript", "js_script"]:
            # QuickJS Postman-style JavaScript 预请求脚本执行
            script_code = action.get("value", "") or action.get("script", "")
            if script_code and isinstance(script_code, str):
                variables, req_headers, req_params, req_path, req_body, js_err = run_quickjs_pre_script(
                    script_code=script_code,
                    variables=variables,
                    headers=req_headers,
                    params=req_params,
                    path=req_path,
                    body=req_body
                )
                if js_err:
                    variables["_script_error"] = f"[JS执行异常] {js_err}"
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

    # 前置操作结算完毕后，构造全量上下文插值变量池
    # 结合: headers + params + variables，确保前置操作注入的任意参数、请求头或临时变量均可直接在 Body JSON 中以 {{key}} 引用
    combined_ctx: Dict[str, Any] = {}
    combined_ctx.update(req_headers)
    combined_ctx.update(req_params)
    combined_ctx.update(variables)

    final_headers = {k: render_with_variables(v, combined_ctx, auth_token) for k, v in req_headers.items()}
    final_params = {k: render_with_variables(v, combined_ctx, auth_token) for k, v in req_params.items()}
    final_body = render_with_variables(req_body, combined_ctx, auth_token)
    final_path = render_with_variables(req_path, combined_ctx, auth_token)

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

        # 7. JavaScript Postman Tests 脚本断言
        elif act_type in ["javascript", "js_script"]:
            script_code = action.get("value", "") or action.get("expression", "") or action.get("script", "")
            if script_code and isinstance(script_code, str):
                js_assertions, js_extracted, js_err = run_quickjs_post_script(
                    script_code=script_code,
                    status_code=status_code,
                    latency_ms=latency_ms,
                    response_data=response_data,
                    response_text=raw_text,
                    response_headers=resp_headers,
                    context_variables=context_variables or {}
                )
                if js_err:
                    assertions_result.append({
                        "name": name or "JavaScript 断言脚本执行",
                        "type": act_type,
                        "passed": False,
                        "actual": None,
                        "expected": "无运行时异常",
                        "operator": "js_eval",
                        "message": f"脚本执行错误: {js_err}"
                    })
                else:
                    for ja in js_assertions:
                        assertions_result.append({
                            "name": ja.get("name") or "JS 测试断言",
                            "type": act_type,
                            "passed": bool(ja.get("passed")),
                            "actual": None,
                            "expected": None,
                            "operator": "pm.test",
                            "message": ja.get("message", "")
                        })
                    extracted_vars.update(js_extracted)

    # 判定全部断言是否通过 (忽略 extract_variable)
    pure_assertions = [a for a in assertions_result if a.get("type") != "extract_variable"]
    all_passed = all(a["passed"] for a in pure_assertions) if pure_assertions else True

    return all_passed, assertions_result, extracted_vars
