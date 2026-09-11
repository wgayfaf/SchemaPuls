# -*- coding: utf-8 -*-
"""
验证四层资产层级化、职责解耦探测、离线熔断机制与批量克隆的端到端自动化测试
"""
import sys
import io
import asyncio
from httpx import AsyncClient

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"


async def main():
    print("==================================================")
    print("   SchemaPulse - 四层资产层级化与解耦探测验证")
    print("==================================================")

    async with AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # 1. 验证拓扑树聚合接口 (GET /api/topology/tree)
        tree_resp = await client.get("/api/topology/tree")
        assert tree_resp.status_code == 200, f"Tree API failed: {tree_resp.status_code}"
        tree = tree_resp.json()
        assert isinstance(tree, list), "Tree should be a list of environments"
        print(f"[OK] [1/6] 成功获取拓扑整树，当前已包含 {len(tree)} 个环境节点！")
        if tree:
            first_env = tree[0]
            print(f"      - 首个环境: [{first_env['name']}], 下属分组数: {len(first_env['groups'])}")
            if first_env["groups"]:
                first_grp = first_env["groups"][0]
                print(f"      - 首个分组: [{first_grp['name']}], 机器数: {len(first_grp['machines'])}")
                if first_grp["machines"]:
                    first_m = first_grp["machines"][0]
                    print(f"      - 机器: [{first_m['name']}] ({first_m['host']}:{first_m['port']}), 接口探针数: {len(first_m['apis'])}")

        # 2. 创建一个完整的独立四层资产链条
        # 2.1 环境
        env_resp = await client.post("/api/environments", json={
            "name": f"自动化测试环境_{asyncio.get_event_loop().time()}",
            "description": "临时用于四层资产测试的沙箱环境",
            "order_num": 99
        })
        assert env_resp.status_code == 200, f"Create env failed: {env_resp.text}"
        env_data = env_resp.json()
        env_id = env_data["id"]
        print(f"[OK] [2/6] 创建测试环境成功: ID={env_id} ({env_data['name']})")

        # 2.2 分组
        grp_resp = await client.post("/api/groups", json={
            "environment_id": env_id,
            "name": "核心认证服务集群",
            "description": "OAuth2 & User Service"
        })
        assert grp_resp.status_code == 200
        grp_id = grp_resp.json()["id"]
        print(f"      - 创建测试服务分组成功: ID={grp_id}")

        # 2.3 机器节点 A (在线公网节点: httpbin.org:80)
        m_a_resp = await client.post("/api/machines", json={
            "group_id": grp_id,
            "name": "auth-node-01 (在线正常节点)",
            "host": "httpbin.org",
            "port": 80,
            "cron_interval_minutes": 5,
            "email_receivers": ["ops@company.com"]
        })
        assert m_a_resp.status_code == 200
        machine_a_id = m_a_resp.json()["id"]

        # 2.4 机器节点 B (不可达宕机节点: 127.0.0.1:54321 假定端口不开放)
        m_b_resp = await client.post("/api/machines", json={
            "group_id": grp_id,
            "name": "auth-node-02 (模拟离线宕机节点)",
            "host": "127.0.0.1",
            "port": 54321,
            "cron_interval_minutes": 5,
            "retry_threshold": 1,
            "email_receivers": ["alert@company.com"]
        })
        assert m_b_resp.status_code == 200
        machine_b_id = m_b_resp.json()["id"]
        print(f"      - 创建机器节点 A (在线, ID={machine_a_id}) 和 机器节点 B (离线测试, ID={machine_b_id})")

        # 2.5 在机器 A 下创建业务接口探针 1
        api_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["url", "origin"],
            "properties": {
                "url": {"type": "string"},
                "origin": {"type": "string"}
            }
        }
        api1_resp = await client.post("/api/apis", json={
            "machine_id": machine_a_id,
            "name": "用户登录健康心跳 (/get)",
            "http_path": "/get",
            "http_method": "GET",
            "expected_schema": api_schema,
            "cron_interval_minutes": 5,
            "email_receivers": ["dev@company.com"]
        })
        assert api1_resp.status_code == 200
        api1_id = api1_resp.json()["id"]
        print(f"      - 在机器 A 下创建接口探针: ID={api1_id} (/get)")

        # 3. 验证机器节点端口握手探测与在线状态识别
        probe_a_resp = await client.post(f"/api/machines/{machine_a_id}/trigger")
        assert probe_a_resp.status_code == 200
        probe_a_data = probe_a_resp.json()
        assert probe_a_data["tcp_ok"] is True
        print(f"[OK] [3/6] 触发机器 A 端口连通探测成功: TCP连通=True, RTT耗时={probe_a_data['tcp_latency_ms']} ms")

        # 4. 验证机器离线熔断与告警风暴收敛机制
        # 4.1 在机器 B 下挂载一个接口探针
        api2_resp = await client.post("/api/apis", json={
            "machine_id": machine_b_id,
            "name": "离线机器下的支付回调接口",
            "http_path": "/pay/notify",
            "http_method": "POST",
            "expected_schema": {"type": "object"}
        })
        assert api2_resp.status_code == 200
        api2_id = api2_resp.json()["id"]

        # 4.2 触发机器 B 探测 (端口关闭，触发 OFFLINE)
        probe_b_resp = await client.post(f"/api/machines/{machine_b_id}/trigger")
        assert probe_b_resp.status_code == 200
        probe_b_data = probe_b_resp.json()
        assert probe_b_data["tcp_ok"] is False
        print(f"[OK] [4/6] 触发机器 B 端口探测: TCP握手正确判定失败 ({probe_b_data['error_message']})")

        # 检查机器 B 是否被标记为 OFFLINE
        m_b_check = (await client.get(f"/api/machines?group_id={grp_id}")).json()
        mb = next(m for m in m_b_check if m["id"] == machine_b_id)
        assert mb["current_status"] == "OFFLINE", f"Expected OFFLINE, got {mb['current_status']}"
        print(f"      - 机器 B 状态已自动标记为: {mb['current_status']}")

        # 4.3 验证接口探针熔断短路: 触发接口 2 探测，验证其直接短路，不发起真实网络请求
        api2_trigger = await client.post(f"/api/apis/{api2_id}/trigger")
        assert api2_trigger.status_code == 200
        api2_hist = api2_trigger.json()
        assert api2_hist["circuit_broken"] is True, "Expected circuit_broken=True"
        assert "[熔断短路]" in api2_hist["raw_response_snippet"]
        print(f"      - 【熔断机制生效验证通过】: 接口探针 ID={api2_id} 正确触发熔断短路，完全跳过发起无效网络请求！")

        # 5. 验证在线机器 A 名下接口业务校验
        api1_trigger = await client.post(f"/api/apis/{api1_id}/trigger")
        assert api1_trigger.status_code == 200
        api1_hist = api1_trigger.json()
        assert api1_hist["circuit_broken"] is False
        assert api1_hist["http_status_code"] == 200
        assert api1_hist["schema_matched"] is True
        assert api1_hist["is_healthy"] is True
        print(f"[OK] [5/6] 机器 A 名下接口探针业务与 Schema 契约校验通过: 状态码={api1_hist['http_status_code']}, 耗时={api1_hist['http_latency_ms']} ms")

        # 6. 验证批量复制接口探针能力 (将机器 A 的接口克隆到机器 B)
        clone_resp = await client.post(f"/api/machines/{machine_a_id}/clone-apis", json={
            "target_machine_ids": [machine_b_id],
            "override_existing": False
        })
        assert clone_resp.status_code == 200
        clone_data = clone_resp.json()
        print(f"[OK] [6/6] 一键批量克隆接口探针成功: {clone_data['message']}")

        # 验证机器 B 名下是否多出了来自机器 A 的接口
        apis_b = (await client.get(f"/api/apis?machine_id={machine_b_id}")).json()
        cloned_api = next((a for a in apis_b if a["http_path"] == "/get"), None)
        assert cloned_api is not None, "Cloned API /get not found on machine B"
        print(f"      - 成功在目标机器 B 名下找到同步克隆的新探针: [{cloned_api['name']}] (路径: {cloned_api['http_path']})")

        # 清理测试环境
        del_env = await client.delete(f"/api/environments/{env_id}")
        assert del_env.status_code == 200
        print(f"      - 级联清理测试沙箱环境成功！")

    print("\n>>> 四层拓扑架构、解耦探测、离线熔断与批量克隆全链路 100% 验证通过！<<<")

if __name__ == "__main__":
    asyncio.run(main())
