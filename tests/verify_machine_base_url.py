import requests
import json
import sys

BASE_API = "http://127.0.0.1:8000"

def test_machine_base_url():
    print("=== Testing Machine Node base_url & API Probe Inheritance ===")

    # 1. Backend reachable
    res = requests.get(f"{BASE_API}/api/dashboard/summary")
    assert res.status_code == 200, f"Summary failed: {res.text}"
    print("[PASS] Backend API is reachable.")

    # 2. Get or create Environment
    envs = requests.get(f"{BASE_API}/api/environments").json()
    assert len(envs) > 0, "No environments found"
    env_id = envs[0]["id"]
    print(f"[PASS] Using environment ID {env_id} ({envs[0]['name']})")

    # 3. Create or update MachineNode with base_url = 'https://httpbin.org'
    mach_payload = {
        "name": "HTTPS专用服务节点",
        "host": "httpbin.org",
        "port": 80,
        "base_url": "https://httpbin.org",
        "environment_id": env_id,
        "cron_interval_minutes": 5,
        "email_receivers": ["admin@company.com"]
    }
    machines = requests.get(f"{BASE_API}/api/machines").json()
    existing_mach = next((m for m in machines if m["name"] == mach_payload["name"]), None)
    if existing_mach:
        m_id = existing_mach["id"]
        put_res = requests.put(f"{BASE_API}/api/machines/{m_id}", json=mach_payload)
        assert put_res.status_code == 200
        mach_data = put_res.json()
    else:
        post_res = requests.post(f"{BASE_API}/api/machines", json=mach_payload)
        assert post_res.status_code == 200
        mach_data = post_res.json()
        m_id = mach_data["id"]

    assert mach_data.get("base_url") == "https://httpbin.org", f"Machine base_url mismatch: {mach_data}"
    print(f"[PASS] MachineNode {m_id} configured with base_url: {mach_data['base_url']}")

    # 4. Test debug run inheriting machine's base_url (no base_url in payload)
    run_payload = {
        "machine_id": m_id,
        "base_url": None,
        "http_method": "GET",
        "http_path": "/get?from=machine_test",
        "http_params": [{"key": "ver", "value": "2.0", "enabled": True}],
        "http_headers": [{"key": "Accept", "value": "application/json", "enabled": True}]
    }
    run_res = requests.post(f"{BASE_API}/api/apis/test-run", json=run_payload)
    assert run_res.status_code == 200, f"Test run failed: {run_res.text}"
    run_data = run_res.json()
    resolved_url = run_data.get("resolved_url") or run_data.get("request_url")
    print(f"[PASS] Test run with inherited machine base_url: {resolved_url}")
    assert "https://httpbin.org/get" in resolved_url, f"Expected https://httpbin.org/get, got {resolved_url}"
    assert run_data.get("status_code") == 200

    # 5. Create API probe with custom override base_url vs default machine base_url
    api_payload = {
        "machine_id": m_id,
        "name": "继承机器地址的订单接口",
        "base_url": None, # Will inherit machine.base_url
        "http_method": "GET",
        "http_path": "/get?action=order",
        "cron_interval_minutes": 5,
        "is_active": True,
        "email_receivers": ["api-team@company.com"],
        "expected_schema": {
            "type": "object",
            "required": ["args", "headers", "origin", "url"]
        }
    }
    api_res = requests.post(f"{BASE_API}/api/apis", json=api_payload)
    assert api_res.status_code == 200, f"Create API failed: {api_res.text}"
    api_obj = api_res.json()
    api_id = api_obj["id"]
    print(f"[PASS] Created API probe ID {api_id}")

    # 6. Trigger execution of this API probe -> should use machine.base_url
    trig_res = requests.post(f"{BASE_API}/api/apis/{api_id}/trigger")
    assert trig_res.status_code == 200, f"Trigger failed: {trig_res.text}"
    trig_data = trig_res.json()
    print(f"[PASS] API Probe trigger result: healthy={trig_data.get('is_healthy')}, code={trig_data.get('http_status_code')}, latency={trig_data.get('http_latency_ms')}ms")
    assert trig_data.get("is_healthy") is True
    assert trig_data.get("schema_matched") is True

    # 7. Check list_apis: full_url should use machine.base_url
    apis = requests.get(f"{BASE_API}/api/apis").json()
    target_api = next((a for a in apis if a["id"] == api_id), None)
    assert target_api is not None
    print(f"[PASS] API listed full_url: {target_api.get('full_url')}")
    assert "https://httpbin.org/get" in target_api.get("full_url")

    # Clean up
    del_res = requests.delete(f"{BASE_API}/api/apis/{api_id}")
    assert del_res.status_code == 200
    print("[PASS] Test API probe deleted.")

    print("\n>>> ALL MACHINE BASE_URL TESTS PASSED! <<<\n")

if __name__ == "__main__":
    test_machine_base_url()
