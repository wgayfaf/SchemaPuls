import zipfile
import json
import sys

def inspect():
    with zipfile.ZipFile(r'c:\Users\wgayf\Desktop\wuyu\SchemaPulse\table.zip') as z:
        for info in z.infolist():
            raw_bytes = z.read(info.filename)
            # 解决中文文件名乱码
            try:
                fname = info.filename.encode('cp437').decode('gbk')
            except:
                try:
                    fname = info.filename.encode('cp437').decode('utf-8')
                except:
                    fname = info.filename
            
            print(f"================ File: {fname} ({info.file_size} bytes) ================")
            try:
                data = json.loads(raw_bytes.decode('utf-8'))
                if "_postman_variable_scope" in data or "values" in data:
                    print(f"类型: Postman 环境变量 (Environment)")
                    print(f"环境名: {data.get('name')}")
                    print(f"变量列表:")
                    for v in data.get("values", []):
                        print(f"  - {v.get('key')} = {v.get('value')} (enabled={v.get('enabled')})")
                elif "info" in data and "item" in data:
                    print(f"类型: Postman 接口集合 (Collection v2.1.0)")
                    print(f"集合名称: {data['info'].get('name')}")
                    
                    # 递归提取所有请求
                    def extract_items(items, prefix=""):
                        requests = []
                        for it in items:
                            name = it.get("name", "")
                            full_name = f"{prefix} / {name}" if prefix else name
                            if "item" in it:
                                requests.extend(extract_items(it["item"], full_name))
                            elif "request" in it:
                                req = it["request"]
                                url_info = req.get("url", {})
                                raw_url = url_info.get("raw", "") if isinstance(url_info, dict) else str(url_info)
                                method = req.get("method", "GET")
                                
                                # 事件（prerequest, test）
                                events = it.get("event", [])
                                pre_scripts = [e.get("script", {}).get("exec", []) for e in events if e.get("listen") == "prerequest"]
                                test_scripts = [e.get("script", {}).get("exec", []) for e in events if e.get("listen") == "test"]
                                
                                # headers
                                headers = req.get("header", [])
                                
                                # body
                                body = req.get("body", {})
                                
                                requests.append({
                                    "full_name": full_name,
                                    "method": method,
                                    "raw_url": raw_url,
                                    "url_info": url_info,
                                    "headers_count": len(headers),
                                    "has_pre": len(pre_scripts) > 0,
                                    "has_test": len(test_scripts) > 0,
                                    "body_mode": body.get("mode") if isinstance(body, dict) else None,
                                    "raw_body": body.get("raw") if isinstance(body, dict) else None,
                                    "pre_script_sample": "\n".join(pre_scripts[0]) if pre_scripts else "",
                                    "test_script_sample": "\n".join(test_scripts[0]) if test_scripts else ""
                                })
                        return requests
                    
                    reqs = extract_items(data["item"])
                    print(f"解析到接口总数: {len(reqs)}")
                    for idx, r in enumerate(reqs, 1):
                        print(f"\n[{idx}] {r['method']} {r['raw_url']}")
                        print(f"    名称路径: {r['full_name']}")
                        print(f"    Headers 数: {r['headers_count']}, Body 模式: {r['body_mode']}")
                        if r['has_pre']:
                            print(f"    存在 Pre-request 脚本 (长度: {len(r['pre_script_sample'])} 字符)")
                        if r['has_test']:
                            print(f"    存在 Test 断言脚本 (长度: {len(r['test_script_sample'])} 字符)")
            except Exception as e:
                print(f"解析出错: {e}")

if __name__ == "__main__":
    inspect()
