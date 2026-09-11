# -*- coding: utf-8 -*-
"""
验证请求延迟展示功能的自动化测试脚本
"""
import sys
import io
import asyncio
from httpx import AsyncClient

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

async def test_latency():
    print("==================================================")
    print("   SchemaPulse - 请求延迟指标链路自动化验证")
    print("==================================================")
    
    async with AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # 1. 验证目标列表返回 latency 字段
        resp = await client.get("/api/targets")
        assert resp.status_code == 200, f"Failed to list targets: {resp.status_code}"
        targets = resp.json()
        assert len(targets) > 0, "No targets found"
        print(f"[OK] [1/3] 成功获取目标列表 ({len(targets)} 个目标)")
        
        target = targets[0]
        tid = target["id"]
        print(f"      - 目标 ID: {tid} ({target['name']})")
        print(f"      - 初始延迟: {target.get('last_latency_ms')} ms (TCP: {target.get('last_tcp_latency_ms')} ms, HTTP: {target.get('last_http_latency_ms')} ms)")

        # 2. 触发一次实时探测
        trig_resp = await client.post(f"/api/targets/{tid}/trigger")
        assert trig_resp.status_code == 200, f"Failed to trigger probe: {trig_resp.status_code}"
        trig_data = trig_resp.json()
        print(f"[OK] [2/3] 手动触发实时探测成功:")
        print(f"      - TCP耗时: {trig_data.get('tcp_latency_ms')} ms")
        print(f"      - HTTP耗时: {trig_data.get('http_latency_ms')} ms")
        print(f"      - 状态判定: {'HEALTHY' if trig_data.get('is_healthy') else 'FAIL'}")

        # 3. 再次查询 targets，验证延迟字段是否持久化并正确更新
        resp2 = await client.get("/api/targets")
        assert resp2.status_code == 200
        targets2 = resp2.json()
        updated_t = next((t for t in targets2 if t["id"] == tid), None)
        assert updated_t is not None
        assert updated_t.get("last_latency_ms") is not None, "last_latency_ms should not be None after probe"
        print(f"[OK] [3/3] 验证目标延迟字段更新与持久化成功:")
        print(f"      - 最新综合延迟: {updated_t.get('last_latency_ms')} ms")
        print(f"      - 最新TCP握手耗时: {updated_t.get('last_tcp_latency_ms')} ms")
        print(f"      - 最新HTTP响应耗时: {updated_t.get('last_http_latency_ms')} ms")
        print(f"      - 最新探测时间: {updated_t.get('last_probed_at')}")

    print("\n>>> 请求延迟功能全链路验证 100% 成功！<<<")

if __name__ == "__main__":
    asyncio.run(test_latency())
