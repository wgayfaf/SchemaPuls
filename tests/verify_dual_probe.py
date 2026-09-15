import os
import sys
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

base_url = "http://127.0.0.1:8000"

def test_machine_dual_probe():
    print("==================================================")
    print("   SchemaPulse - 机器主机(Ping)+端口(TCP)双重探活验证")
    print("==================================================")

    # 1. 验证不可达机器 (192.0.2.1:22，保留不可路由私有测试网段，Ping 必失败)
    res_unreach = requests.post(f"{base_url}/api/machines", json={
        "name": "fake-unreachable-node",
        "host": "192.0.2.1",
        "port": 22,
        "cron_interval_minutes": 5,
        "retry_threshold": 3,
        "silence_minutes": 30,
        "email_receivers": [],
        "group_id": 1,
        "environment_id": 1
    })
    unreach_node = res_unreach.json()
    unreach_id = unreach_node["id"]
    try:
        trigger_res = requests.post(f"{base_url}/api/machines/{unreach_id}/trigger")
        assert trigger_res.status_code == 200, f"Trigger failed: {trigger_res.text}"
        m_unreach = [m for m in requests.get(f"{base_url}/api/machines").json() if m["id"] == unreach_id][0]
        assert m_unreach["current_status"] == "OFFLINE", f"Expected OFFLINE, got {m_unreach['current_status']}"
        assert m_unreach["ping_ok"] is False, f"ping_ok should be False, got {m_unreach['ping_ok']}"
        assert m_unreach["tcp_ok"] is False, f"tcp_ok should be False, got {m_unreach['tcp_ok']}"
        assert "Ping" in m_unreach["last_error_message"], f"Error message should mention Ping: {m_unreach['last_error_message']}"
        print("[OK] [1/3] 虚假不可达 IP (192.0.2.1:22) 判定为 OFFLINE，成功杜绝虚拟网卡 Fake TCP 误判:")
        print(f"      - 主机状态: {m_unreach['current_status']}")
        print(f"      - Ping 通: {m_unreach['ping_ok']}")
        print(f"      - 诊断错误: {m_unreach['last_error_message']}")
    finally:
        requests.delete(f"{base_url}/api/machines/{unreach_id}")

    # 2. 验证可达主机且端口开放机器 (Node 1: httpbin.org:80)
    r1 = requests.post(f"{base_url}/api/machines/1/trigger")
    assert r1.status_code == 200, f"Trigger node 1 failed: {r1.text}"
    m1 = [m for m in requests.get(f"{base_url}/api/machines").json() if m["id"] == 1][0]
    assert m1["current_status"] == "ONLINE", f"Node 1 should be ONLINE, got {m1['current_status']}"
    assert m1["ping_ok"] is True, f"Node 1 ping_ok should be True, got {m1['ping_ok']}"
    assert m1["tcp_ok"] is True, f"Node 1 tcp_ok should be True, got {m1['tcp_ok']}"
    print("[OK] [2/3] 真实主机与开放端口 (httpbin.org:80) 判定为 ONLINE:")
    print(f"      - 主机状态: {m1['current_status']}")
    print(f"      - Ping 耗时: {m1['last_ping_latency_ms']} ms")
    print(f"      - TCP 耗时: {m1['last_tcp_latency_ms']} ms")

    # 3. 验证主机在线但服务端口关闭节点 (127.0.0.1:49999)
    res_degraded = requests.post(f"{base_url}/api/machines", json={
        "name": "test-closed-port",
        "host": "127.0.0.1",
        "port": 49999,
        "cron_interval_minutes": 5,
        "retry_threshold": 3,
        "silence_minutes": 30,
        "email_receivers": [],
        "group_id": 1,
        "environment_id": 1
    })
    test_node = res_degraded.json()
    temp_id = test_node["id"]
    try:
        requests.post(f"{base_url}/api/machines/{temp_id}/trigger")
        m_temp = [m for m in requests.get(f"{base_url}/api/machines").json() if m["id"] == temp_id][0]
        assert m_temp["current_status"] == "DEGRADED", f"Expected DEGRADED, got {m_temp['current_status']}"
        assert m_temp["ping_ok"] is True, f"Ping should be True, got {m_temp['ping_ok']}"
        assert m_temp["tcp_ok"] is False, f"TCP should be False, got {m_temp['tcp_ok']}"
        print("[OK] [3/3] 主机在线但服务端口关闭 (127.0.0.1:49999) 判定为 DEGRADED (告警/降级):")
        print(f"      - 综合状态: {m_temp['current_status']}")
        print(f"      - Ping 通: {m_temp['ping_ok']} ({m_temp['last_ping_latency_ms']} ms)")
        print(f"      - TCP 通: {m_temp['tcp_ok']}")
        print(f"      - 诊断错误: {m_temp['last_error_message']}")
    finally:
        requests.delete(f"{base_url}/api/machines/{temp_id}")

    print("\n>>> 机器主机在线(Ping) + 服务端口(TCP) 双重探活逻辑验证 100% 通过！<<<")

if __name__ == "__main__":
    test_machine_dual_probe()
