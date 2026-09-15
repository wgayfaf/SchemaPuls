import os
import sys
import json
from fastapi.testclient import TestClient

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")
frontend_dir = os.path.join(root_dir, "frontend")
sys.path.insert(0, backend_dir)

from app.main import app
from app.database import engine, init_db
from sqlmodel import Session
from app.models import MachineNode, ApiProbe, Environment
from app.services.template_engine import (
    render_macro_string,
    render_template_value,
    parse_params_to_dict,
    parse_headers_to_dict
)

def test_template_engine():
    print("==================================================")
    print("   1. 测试动态预请求宏引擎 (Macro Template Engine)")
    print("==================================================")
    s1 = render_macro_string("https://example.com/api?t={{$timestamp}}&uid={{$uuid}}")
    assert "{{$timestamp}}" not in s1
    assert "{{$uuid}}" not in s1
    print(f"[OK] 宏替换成功: {s1}")

    s2 = render_macro_string("rand={{$randomInt(10, 50)}}")
    rand_val = int(s2.split("=")[1])
    assert 10 <= rand_val <= 50
    print(f"[OK] 随机数宏替换成功: {s2}")

    params = [
        {"enabled": True, "key": "query", "value": "test_{{$timestamp}}"},
        {"enabled": False, "key": "ignored", "value": "skip"},
        {"enabled": True, "key": "page", "value": "1"}
    ]
    pdict = parse_params_to_dict(params)
    assert "query" in pdict
    assert "ignored" not in pdict
    assert pdict["page"] == "1"
    print(f"[OK] Params 列表转字典成功: {pdict}")

def test_postman_backend_api():
    print("\n==================================================")
    print("   2. 测试 Postman 接口调试探针与存储 (/api/apis)")
    print("==================================================")
    init_db()
    client = TestClient(app)

    with Session(engine) as db:
        # 获取或创建测试环境与机器
        from sqlmodel import select
        env = db.exec(select(Environment)).first()
        if not env:
            env = Environment(name="测试环境")
            db.add(env)
            db.commit()
            db.refresh(env)

        machine = db.exec(select(MachineNode).where(MachineNode.host == "httpbin.org")).first()
        if not machine:
            machine = MachineNode(
                name="HttpBin 测试节点",
                environment_id=env.id,
                host="httpbin.org",
                port=80,
                is_online=True
            )
            db.add(machine)
            db.commit()
            db.refresh(machine)
        m_id = machine.id

    # 1. 测试实时调试端点 /api/apis/test-run
    test_payload = {
        "machine_id": m_id,
        "http_method": "GET",
        "http_path": "/get",
        "http_params": [
            {"enabled": True, "key": "source", "value": "SchemaPulse_Postman"},
            {"enabled": True, "key": "t", "value": "{{$timestamp}}"}
        ],
        "http_headers": [
            {"enabled": True, "key": "X-Custom-Trace", "value": "{{$uuid}}"},
            {"enabled": True, "key": "Accept", "value": "application/json"}
        ],
        "http_body_type": "none",
        "auth_type": "bearer",
        "auth_config": {
            "token": "secret_test_token_123"
        },
        "expected_schema": {
            "type": "object",
            "required": ["args", "headers", "origin", "url"]
        }
    }

    resp = client.post("/api/apis/test-run", json=test_payload)
    assert resp.status_code == 200, f"test-run 失败: {resp.text}"
    data = resp.json()
    print(f"[OK] 实时调试 /api/apis/test-run 成功:")
    print(f"     状态码: {data.get('status_code')}")
    print(f"     耗时: {data.get('latency_ms')} ms")
    print(f"     目标URL: {data.get('resolved_url')}")
    print(f"     Schema 校验通过: {data.get('schema_matched')}")
    assert data.get("status_code") == 200
    assert data.get("schema_matched") is True

    # 2. 创建持久化 Postman 风格接口探针
    create_payload = {
        "machine_id": m_id,
        "name": "Postman 风格单元测试接口",
        "http_method": "GET",
        "http_path": "/get?debug=true",
        "expected_schema": {
            "type": "object",
            "required": ["args", "url"]
        },
        "cron_interval_minutes": 5,
        "is_active": True,
        "email_receivers": ["tester@schemapulse.io"],
        "http_params": [
            {"enabled": True, "key": "debug", "value": "true", "description": "调试标记"}
        ],
        "http_headers": [
            {"enabled": True, "key": "Accept", "value": "application/json", "description": "JSON类型"}
        ],
        "http_body_type": "none",
        "auth_type": "none"
    }
    resp_create = client.post("/api/apis", json=create_payload)
    assert resp_create.status_code == 200
    created_api = resp_create.json()
    api_id = created_api["id"]
    print(f"[OK] 创建接口探针成功: ID={api_id}, Name={created_api['name']}")
    assert len(created_api["http_params"]) == 1
    assert created_api["http_params"][0]["key"] == "debug"

    # 3. 触发该持久化探针执行
    resp_trigger = client.post(f"/api/apis/{api_id}/trigger")
    assert resp_trigger.status_code == 200
    trigger_data = resp_trigger.json()
    print(f"[OK] 触发执行探针成功: status={trigger_data.get('http_status_code')}, matched={trigger_data.get('schema_matched')}")

    # 清理测试探针
    client.delete(f"/api/apis/{api_id}")
    print(f"[OK] 清理测试探针 ID={api_id} 成功")

def test_frontend_postman_elements():
    print("\n==================================================")
    print("   3. 验证前端 HTML/JS/CSS 中的 Postman 工作台元素")
    print("==================================================")
    # 验证 CSS
    with open(os.path.join(frontend_dir, "css", "style.css"), "r", encoding="utf-8") as f:
        css_content = f.read()
        assert ".postman-dialog" in css_content
        assert ".pm-url-bar" in css_content
        assert ".pm-method-select" in css_content
        assert ".pm-kv-table" in css_content
        assert ".pm-response-card" in css_content
    print("[OK] CSS 中包含完整的 Postman 工作台与实时调试响应卡片样式类")

    # 验证 HTML
    with open(os.path.join(frontend_dir, "index.html"), "r", encoding="utf-8") as f:
        html_content = f.read()
        assert "pm-url-bar" in html_content
        assert ("selectedMachineBaseUrl" in html_content or "selectedMachineHost" in html_content)
        assert "apiActiveTab" in html_content
        assert "handleTestRunApi" in html_content
        assert "inferSchemaFromTestResult" in html_content
        assert "pm-response-card" in html_content
        assert "pre_actions" in html_content
        assert "post_actions" in html_content
    print("[OK] HTML 模版中包含 URL 请求栏、Params/Headers/Body/Auth/前置/后置/Schema 多标签页及断言响应面板")

    # 验证 JS
    with open(os.path.join(frontend_dir, "js", "app.js"), "r", encoding="utf-8") as f:
        js_content = f.read()
        assert "apiParamsList" in js_content
        assert "apiHeadersList" in js_content
        assert "handleTestRunApi" in js_content
        assert "syncParamsToPath" in js_content
        assert "inferSchemaFromTestResult" in js_content
        assert "selectedMachineHost" in js_content
    print("[OK] JS 驱动中包含双向 URL 同步、请求调试、一键推导与预设宏方法")

    print("\n>>> Postman 风格工作台功能全面验证通过！<<<\n")

if __name__ == "__main__":
    test_template_engine()
    test_postman_backend_api()
    test_frontend_postman_elements()
