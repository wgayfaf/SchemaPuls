import os
import sys

# 确保在 Windows 控制台环境下输出 UTF-8 字符不报错
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient

# 添加 backend 到系统路径
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, backend_dir)

from app.main import app

def run_tests():
    print("==================================================")
    print("   SchemaPulse - 第一阶段原型自动化功能测试")
    print("==================================================")

    with TestClient(app) as client:
        # 1. 测试根路径
        resp = client.get("/")
        assert resp.status_code == 200
        print("[OK] [1/4] 根路径检查通过:", resp.json())

        # 2. 测试 Schema 自动推导接口
        sample_json = {
            "code": 0,
            "message": "success",
            "data": {
                "user_id": 1001,
                "user_name": "Antigravity",
                "is_admin": True
            }
        }
        resp = client.post("/api/tools/infer-schema", json={"sample_json": sample_json, "strict_mode": True})
        assert resp.status_code == 200
        schema_result = resp.json()["schema"]
        print("[OK] [2/4] Schema 自动推导接口测试成功，生成的 Draft-7 结构如下:")
        print("      - 类型:", schema_result.get("type"))
        print("      - 严格模式(additionalProperties):", schema_result.get("additionalProperties"))
        print("      - 识别到的字段:", list(schema_result.get("properties", {}).keys()))

        # 3. 测试创建监控目标
        target_payload = {
            "name": "公网在线健康检查目标",
            "host": "httpbin.org",
            "port": 80,
            "http_path": "/get",
            "http_method": "GET",
            "cron_interval_minutes": 5,
            "expected_schema": {
                "type": "object",
                "required": ["headers", "origin", "url"],
                "properties": {
                    "origin": {"type": "string"},
                    "url": {"type": "string"},
                    "headers": {"type": "object"}
                }
            },
            "retry_threshold": 3,
            "silence_minutes": 30,
            "email_receivers": ["ops-team@company.com", "oncall@company.com"]
        }
        resp = client.post("/api/targets", json=target_payload)
        assert resp.status_code == 200
        target = resp.json()
        target_id = target["id"]
        print(f"[OK] [3/4] 监控目标创建成功: ID={target_id}, 名称={target['name']}")

        # 4. 测试即时触发探测接口 (Trigger Probe)
        print(f"   -> 正在执行即时探活与 Schema 断言: target_id={target_id} ...")
        resp = client.post(f"/api/targets/{target_id}/trigger")
        assert resp.status_code == 200
        probe_res = resp.json()
        print(f"[OK] [4/4] 即时探测执行成功！返回结果:")
        print(f"      - TCP 握手: {'连通' if probe_res['tcp_ok'] else '未连通'} (耗时: {probe_res['tcp_latency_ms']}ms)")
        print(f"      - HTTP 状态码: {probe_res['http_status_code']} (耗时: {probe_res['http_latency_ms']}ms)")
        print(f"      - Schema 匹配: {'完全匹配' if probe_res['schema_matched'] else '不匹配'}")
        print(f"      - 综合健康判定: {'[HEALTHY]' if probe_res['is_healthy'] else '[UNHEALTHY]'}")

    print("\n>>> 第一阶段后端原型全流程链路自测 100% 通过！<<<\n")

if __name__ == "__main__":
    run_tests()
