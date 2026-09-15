import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_api_endpoints():
    try:
        # 1. 查询机器列表
        res = requests.get(f"{BASE_URL}/api/machines")
        print("GET /api/machines status:", res.status_code)
        if res.status_code != 200:
            print("Server not responding properly, might need restart")
            return False

        machines = res.json()
        print(f"Found {len(machines)} machines")
        if not machines:
            print("No machines found")
            return False

        m0 = machines[0]
        m_id = m0["id"]
        print(f"Testing with machine id={m_id}, name={m0['name']}")

        # 2. 查询机器所属环境
        env_res = requests.get(f"{BASE_URL}/api/machines/{m_id}/environment")
        print("GET /api/machines/{id}/environment status:", env_res.status_code)
        print("Environment data:", env_res.json())
        env_data = env_res.json()
        env_id = env_data["environment_id"]

        if env_id:
            # 3. 更新环境变量
            put_res = requests.put(f"{BASE_URL}/api/environments/{env_id}/variables", json={
                "variables": {
                    "TEST_VAR": "schema_pulse_val_123",
                    "BASE_PREFIX": "api_v1"
                }
            })
            print("PUT /api/environments/{id}/variables status:", put_res.status_code)
            print("Updated env:", put_res.json())

            # 4. 执行 test-run 在线调试，验证环境变量是否自动注入并在 JS 脚本中通过 pm.environment.set 修改
            test_run_payload = {
                "machine_id": m_id,
                "http_method": "GET",
                "http_path": "/get?prefix={{BASE_PREFIX}}",
                "http_headers": [{"enabled": True, "key": "X-Test-Var", "value": "{{TEST_VAR}}"}],
                "http_params": [],
                "http_body_type": "none",
                "pre_actions": [
                    {
                        "type": "javascript",
                        "enabled": True,
                        "value": """
                        pm.variables.set("PRE_CALC", "calc_" + pm.environment.get("TEST_VAR"));
                        pm.environment.set("DYNAMIC_PRE", "pre_updated_ok");
                        """
                    }
                ],
                "post_actions": [
                    {
                        "type": "javascript",
                        "enabled": True,
                        "value": """
                        pm.test("Status is valid", function() {
                            pm.expect(pm.response.code).to.be.above(0);
                        });
                        pm.environment.set("POST_TOKEN", "new_token_777");
                        """
                    }
                ]
            }
            tr_res = requests.post(f"{BASE_URL}/api/apis/test-run", json=test_run_payload)
            print("POST /api/apis/test-run status:", tr_res.status_code)
            tr_data = tr_res.json()
            print("Test-run environment echo:", tr_data.get("environment"))
            print("Rendered headers:", tr_data.get("rendered_headers"))
            print("Rendered path:", tr_data.get("resolved_url") or tr_data.get("request_url"))

            # 5. 重新拉取环境，验证持久化生效
            get_env = requests.get(f"{BASE_URL}/api/environments/{env_id}/variables").json()
            print("Verification GET /api/environments/{id}/variables:", get_env)
            assert get_env["variables"].get("POST_TOKEN") == "new_token_777", "POST_TOKEN not persisted!"
            assert get_env["variables"].get("DYNAMIC_PRE") == "pre_updated_ok", "DYNAMIC_PRE not persisted!"
            print("[SUCCESS] All API tests passed successfully!")
            return True

    except Exception as e:
        print("Request failed:", e)
        return False

if __name__ == "__main__":
    test_api_endpoints()
