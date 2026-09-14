import requests
import json
import sys

BASE_API = "http://127.0.0.1:8000"

def test_base_url_feature():
    print("=== Testing Environment & API Probe base_url Feature ===")
    
    # 1. Check backend health
    res = requests.get(f"{BASE_API}/api/dashboard/summary")
    assert res.status_code == 200, f"Summary failed: {res.text}"
    print("[PASS] Backend API is reachable.")

    # 2. Test Environment with base_url
    env_payload = {
        "name": "自动化测试环境_HTTPS",
        "description": "用于验证 Base URL 域名与 https 支持的环境",
        "base_url": "https://httpbin.org",
        "order_num": 99
    }
    # Check if exists
    envs = requests.get(f"{BASE_API}/api/environments").json()
    existing_env = next((e for e in envs if e["name"] == env_payload["name"]), None)
    if existing_env:
        env_id = existing_env["id"]
        put_res = requests.put(f"{BASE_API}/api/environments/{env_id}", json=env_payload)
        assert put_res.status_code == 200
        env_data = put_res.json()
    else:
        post_res = requests.post(f"{BASE_API}/api/environments", json=env_payload)
        assert post_res.status_code == 200
        env_data = post_res.json()
        env_id = env_data["id"]
    
    assert env_data.get("base_url") == "https://httpbin.org", f"base_url mismatch: {env_data}"
    print(f"[PASS] Environment created/updated with base_url: {env_data['base_url']}")

    # 3. Create or get a machine in this environment
    machines = requests.get(f"{BASE_API}/api/machines").json()
    test_machine = next((m for m in machines if m["environment_id"] == env_id), None)
    if not test_machine:
        mach_res = requests.post(f"{BASE_API}/api/machines", json={
            "environment_id": env_id,
            "name": "Httpbin测试宿主机",
            "host": "httpbin.org",
            "port": 80,
            "cron_interval_minutes": 5,
            "email_receivers": ["admin@company.com"]
        })
        assert mach_res.status_code == 200
        test_machine = mach_res.json()
    print(f"[PASS] Machine ready: {test_machine['id']} ({test_machine['host']}:{test_machine['port']})")

    # 4. Test debug run (POST /api/apis/test-run) using base_url HTTPS
    test_run_payload = {
        "machine_id": test_machine["id"],
        "base_url": "https://httpbin.org",
        "http_method": "GET",
        "http_path": "/get?foo=bar",
        "http_params": [{"key": "tag", "value": "schemapulse", "enabled": True}],
        "http_headers": [{"key": "Accept", "value": "application/json", "enabled": True}]
    }
    run_res = requests.post(f"{BASE_API}/api/apis/test-run", json=test_run_payload)
    assert run_res.status_code == 200, f"Test run failed: {run_res.text}"
    run_data = run_res.json()
    print(f"[PASS] Test run resolved URL: {run_data.get('resolved_url')}")
    assert "https://httpbin.org/get" in run_data.get("resolved_url"), f"Unexpected resolved_url: {run_data}"
    assert run_data.get("status_code") == 200, f"Status code not 200: {run_data}"

    # 5. Create an API Probe with base_url
    api_payload = {
        "machine_id": test_machine["id"],
        "name": "HTTPS 订单网关接口",
        "base_url": "https://httpbin.org",
        "http_method": "GET",
        "http_path": "/get?biz=order",
        "cron_interval_minutes": 5,
        "is_active": True,
        "email_receivers": ["devops@company.com"],
        "http_params": [{"key": "limit", "value": "10", "enabled": True}],
        "http_headers": [{"key": "Accept", "value": "application/json", "enabled": True}],
        "expected_schema": {
            "type": "object",
            "required": ["args", "headers", "origin", "url"],
            "properties": {
                "origin": {"type": "string"},
                "url": {"type": "string"}
            }
        }
    }
    api_res = requests.post(f"{BASE_API}/api/apis", json=api_payload)
    assert api_res.status_code == 200, f"Create API failed: {api_res.text}"
    created_api = api_res.json()
    api_id = created_api["id"]
    assert created_api.get("base_url") == "https://httpbin.org", f"base_url not saved: {created_api}"
    print(f"[PASS] API Probe created with ID {api_id}, base_url={created_api.get('base_url')}")

    # 6. Trigger execution of this API Probe (POST /api/apis/{id}/trigger)
    trigger_res = requests.post(f"{BASE_API}/api/apis/{api_id}/trigger")
    assert trigger_res.status_code == 200, f"Trigger failed: {trigger_res.text}"
    trig_data = trigger_res.json()
    print(f"[PASS] Probe trigger result: healthy={trig_data.get('is_healthy')}, status_code={trig_data.get('http_status_code')}, latency={trig_data.get('http_latency_ms')}ms, schema_matched={trig_data.get('schema_matched')}")
    assert trig_data.get("is_healthy") is True, f"Probe was not healthy: {trig_data}"
    assert trig_data.get("schema_matched") is True, f"Schema mismatch: {trig_data}"

    # 7. Check list_apis response
    apis = requests.get(f"{BASE_API}/api/apis").json()
    target_api = next((a for a in apis if a["id"] == api_id), None)
    assert target_api is not None
    assert target_api.get("base_url") == "https://httpbin.org"
    assert "https://httpbin.org" in target_api.get("full_url"), f"full_url mismatch: {target_api.get('full_url')}"
    print(f"[PASS] API Probe list verified. full_url: {target_api.get('full_url')}")

    # Clean up test probe
    del_res = requests.delete(f"{BASE_API}/api/apis/{api_id}")
    assert del_res.status_code == 200
    print("[PASS] Test API Probe cleaned up successfully.")

    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<\n")

if __name__ == "__main__":
    test_base_url_feature()
