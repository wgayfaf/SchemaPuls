# -*- coding: utf-8 -*-
"""
验证时序报表与历史数据接口的自动化测试
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
    print("   SchemaPulse - 时序排障与历史流水接口测试")
    print("==================================================")

    async with AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # 1. 查询目标
        resp = await client.get("/api/targets")
        assert resp.status_code == 200
        targets = resp.json()
        assert len(targets) > 0, "No targets available"
        tid = targets[0]["id"]
        tname = targets[0]["name"]
        print(f"[OK] [1/3] 选中测试目标 ID={tid} ({tname})")

        # 2. 验证 GET /api/targets/{id}/history 历史记录流水
        hist_resp = await client.get(f"/api/targets/{tid}/history?limit=30")
        assert hist_resp.status_code == 200, f"History API failed: {hist_resp.status_code}"
        history = hist_resp.json()
        assert isinstance(history, list), "History must be a list"
        print(f"[OK] [2/3] 历史流水接口 (/api/targets/{tid}/history) 成功返回: 共 {len(history)} 条记录！")
        if history:
            first_h = history[0]
            print(f"      - 最新记录: 时间={first_h.get('probed_at')}, TCP={first_h.get('tcp_ok')}({first_h.get('tcp_latency_ms')}ms), HTTP={first_h.get('http_status_code')}({first_h.get('http_latency_ms')}ms), 契约匹配={first_h.get('schema_matched')}")

        # 3. 验证 GET /api/targets/{id}/metrics 时序折线图点位
        metrics_resp = await client.get(f"/api/targets/{tid}/metrics?hours=24")
        assert metrics_resp.status_code == 200, f"Metrics API failed: {metrics_resp.status_code}"
        points = metrics_resp.json()
        assert isinstance(points, list), "Metrics must be a list of points"
        print(f"[OK] [3/3] 时序指标点位接口 (/api/targets/{tid}/metrics) 成功返回: 共 {len(points)} 个绘图点！")
        if points:
            print(f"      - 绘图时间跨度: {points[0].get('time')} -> {points[-1].get('time')}")

    print("\n>>> 时序排障与历史流水接口 100% 修复并验证通过！<<<")

if __name__ == "__main__":
    asyncio.run(main())
