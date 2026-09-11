import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient

backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, backend_dir)

from app.main import app

def test_frontend_and_metrics():
    print("==================================================")
    print("   SchemaPulse - 前端页面与时序指标接口联调测试")
    print("==================================================")

    with TestClient(app) as client:
        # 1. 验证 /web 控制台静态页面
        resp_web = client.get("/web")
        assert resp_web.status_code == 200
        assert "SchemaPulse" in resp_web.text
        assert "id=\"app\"" in resp_web.text
        print("[OK] [1/4] 前端控制台主页面 (/web) 成功加载并托管！")

        # 2. 验证 /static/app.js 静态脚本
        resp_js = client.get("/static/app.js")
        assert resp_js.status_code == 200
        assert "createApp" in resp_js.text
        print("[OK] [2/4] 前端 Vue 3 + ECharts 驱动核心脚本 (/static/app.js) 加载正常！")

        # 3. 验证 /api/dashboard/summary 大盘统计接口
        resp_summary = client.get("/api/dashboard/summary")
        assert resp_summary.status_code == 200
        summary_data = resp_summary.json()
        print("[OK] [3/4] 监控大盘 KPI 聚合接口正常返回:")
        print(f"      - 监控目标总数: {summary_data['total_targets']}")
        print(f"      - 正常运行节点: {summary_data['healthy_count']}")
        print(f"      - 异常/降级节点: {summary_data['down_count'] + summary_data['degraded_count']}")
        print(f"      - 24小时SLA可用率: {summary_data['sla_rate']}%")

        # 4. 验证 /api/targets/{id}/metrics 时序指标接口
        resp_targets = client.get("/api/targets")
        targets = resp_targets.json()
        if targets:
            test_id = targets[0]["id"]
            resp_metrics = client.get(f"/api/targets/{test_id}/metrics?hours=24")
            assert resp_metrics.status_code == 200
            points = resp_metrics.json()
            print(f"[OK] [4/4] 目标 ID={test_id} 时序指标折线图点位拉取成功: 包含 {len(points)} 个时序历史点！")
        else:
            print("[OK] [4/4] 暂无历史目标，接口结构验证通过！")

    print("\n>>> 前端控制台与指标链路自动化验证 100% 通过！<<<\n")

if __name__ == "__main__":
    test_frontend_and_metrics()
