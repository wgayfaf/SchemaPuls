import sys
import json
import httpx

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("=" * 60)
    print(">>> SchemaPulse 在线服务端到端真实测试 (E2E Live Test) <<<")
    print("=" * 60)

    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # 1. 检查根路径
    print("\n[Step 1] 测试根路径状态检查: GET /")
    r1 = client.get("/")
    print(f"  状态码: {r1.status_code}")
    print(f"  响应体: {r1.json()}")
    assert r1.status_code == 200

    # 2. 测试 Schema 自动推导接口
    print("\n[Step 2] 测试样例 JSON 自动推导 Schema: POST /api/tools/infer-schema")
    sample_payload = {
        "sample_json": {
            "code": 200,
            "status": "success",
            "server_time": "2026-09-11T15:00:00Z",
            "data": {
                "user_id": 10086,
                "username": "SchemaPulseAdmin",
                "roles": ["admin", "devops"]
            }
        },
        "strict_mode": True
    }
    r2 = client.post("/api/tools/infer-schema", json=sample_payload)
    print(f"  状态码: {r2.status_code}")
    inferred_schema = r2.json()["schema"]
    print("  推导生成的 Schema 核心结构:")
    print(f"    - Schema类型: {inferred_schema.get('type')}")
    print(f"    - 是否严格禁止额外字段: {inferred_schema.get('additionalProperties')}")
    print(f"    - 识别到的字段属性: {list(inferred_schema.get('properties', {}).keys())}")
    assert r2.status_code == 200

    # 3. 创建正常健康目标
    print("\n[Step 3] 创建正常健康监控目标: POST /api/targets")
    healthy_target = {
        "name": "公网网关(健康样本)",
        "host": "httpbin.org",
        "port": 80,
        "http_path": "/get",
        "http_method": "GET",
        "expected_schema": {
            "type": "object",
            "required": ["headers", "origin", "url"],
            "properties": {
                "origin": {"type": "string"},
                "url": {"type": "string"},
                "headers": {"type": "object"}
            }
        },
        "cron_interval_minutes": 5,
        "is_active": True,
        "retry_threshold": 3,
        "silence_minutes": 30,
        "email_receivers": ["alert-team@example.com"]
    }
    r3 = client.post("/api/targets", json=healthy_target)
    print(f"  状态码: {r3.status_code}")
    target1 = r3.json()
    t1_id = target1["id"]
    print(f"  创建成功: Target ID = {t1_id}, 名称 = {target1['name']}")
    assert r3.status_code == 200

    # 4. 即时触发健康目标的探测
    print(f"\n[Step 4] 对健康目标即时触发探测: POST /api/targets/{t1_id}/trigger")
    r4 = client.post(f"/api/targets/{t1_id}/trigger")
    print(f"  状态码: {r4.status_code}")
    probe1 = r4.json()
    print("  探测执行结果快照:")
    print(f"    - TCP 握手: {'连通' if probe1['tcp_ok'] else '失败'} (耗时: {probe1['tcp_latency_ms']}ms)")
    print(f"    - HTTP 状态码: {probe1['http_status_code']} (耗时: {probe1['http_latency_ms']}ms)")
    print(f"    - Schema 是否匹配: {probe1['schema_matched']}")
    print(f"    - 综合健康状态: {'[HEALTHY] 正常' if probe1['is_healthy'] else '[UNHEALTHY] 异常'}")
    assert probe1["is_healthy"] is True

    # 5. 创建模拟破坏性变更的目标
    print("\n[Step 5] 创建模拟破坏性结构突变目标: POST /api/targets")
    broken_target = {
        "name": "模拟突变接口(破坏性变更样本)",
        "host": "httpbin.org",
        "port": 80,
        "http_path": "/get",
        "http_method": "GET",
        "expected_schema": {
            "type": "object",
            "required": ["headers", "origin", "auth_token"],  # 故意缺少 auth_token
            "properties": {
                "origin": {"type": "number"}  # 故意将 string 判定为 number
            },
            "additionalProperties": False  # 严格模式
        },
        "cron_interval_minutes": 5,
        "is_active": True,
        "retry_threshold": 1,
        "silence_minutes": 30,
        "email_receivers": ["oncall@example.com", "devops@example.com"]
    }
    r5 = client.post("/api/targets", json=broken_target)
    print(f"  状态码: {r5.status_code}")
    target2 = r5.json()
    t2_id = target2["id"]
    print(f"  创建成功: Target ID = {t2_id}, 名称 = {target2['name']}")

    # 6. 即时触发突变目标的探测 (验证捕获异常)
    print(f"\n[Step 6] 对突变目标触发即时探测: POST /api/targets/{t2_id}/trigger")
    r6 = client.post(f"/api/targets/{t2_id}/trigger")
    print(f"  状态码: {r6.status_code}")
    probe2 = r6.json()
    print("  探测执行结果快照:")
    print(f"    - TCP 握手: {'连通' if probe2['tcp_ok'] else '失败'} (耗时: {probe2['tcp_latency_ms']}ms)")
    print(f"    - HTTP 状态码: {probe2['http_status_code']} (耗时: {probe2['http_latency_ms']}ms)")
    print(f"    - Schema 是否匹配: {probe2['schema_matched']}")
    print(f"    - 综合健康状态: {'[HEALTHY] 正常' if probe2['is_healthy'] else '[UNHEALTHY] 异常 (成功捕获！)'}")
    print("  捕获到的破坏性结构变更明细:")
    for err in probe2.get("schema_diff_detail", []):
        print(f"      * [{err['field']}] ({err['validator']}): {err['message']}")
    assert probe2["is_healthy"] is False

    # 7. 查看历史记录
    print(f"\n[Step 7] 查询目标的历史探测记录: GET /api/targets/{t2_id}/history")
    r7 = client.get(f"/api/targets/{t2_id}/history")
    print(f"  状态码: {r7.status_code}")
    history_list = r7.json()
    print(f"  已成功落库的历史记录数量: {len(history_list)} 条")

    # 8. 查看目标列表大盘状态
    print("\n[Step 8] 查询监控目标列表与实时状态: GET /api/targets")
    r8 = client.get("/api/targets")
    targets_all = r8.json()
    print(f"  当前系统托管的目标数: {len(targets_all)} 个")
    for t in targets_all:
        print(f"    - ID: {t['id']} | 名称: {t['name']} | 当前状态: {t['current_status']} | 失败计数: {t['consecutive_failures']}")

    print("\n" + "=" * 60)
    print(">>> 恭喜！端到端真实在线测试 100% 成功跑通！<<<")
    print("=" * 60)

if __name__ == "__main__":
    main()
