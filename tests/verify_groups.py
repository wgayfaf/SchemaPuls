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

def test_group_features():
    print("==================================================")
    print("   SchemaPulse - 多环境/业务分组功能自动化测试")
    print("==================================================")

    with TestClient(app) as client:
        # 1. 创建属于不同环境的两个新目标
        payload_staging = {
            "name": "用户中心(Staging预发接口)",
            "group_name": "预发布环境",
            "host": "httpbin.org",
            "port": 80,
            "http_path": "/get",
            "http_method": "GET",
            "cron_interval_minutes": 5,
            "expected_schema": {"type": "object"},
            "email_receivers": ["staging-alert@company.com"]
        }
        r1 = client.post("/api/targets", json=payload_staging)
        assert r1.status_code == 200
        print("[OK] [1/4] 成功创建【预发布环境】监控目标:", r1.json()["name"])

        payload_test = {
            "name": "支付网关(QA测试接口)",
            "group_name": "测试环境",
            "host": "httpbin.org",
            "port": 80,
            "http_path": "/get",
            "http_method": "GET",
            "cron_interval_minutes": 5,
            "expected_schema": {"type": "object"},
            "email_receivers": ["qa-team@company.com"]
        }
        r2 = client.post("/api/targets", json=payload_test)
        assert r2.status_code == 200
        print("[OK] [2/4] 成功创建【测试环境】监控目标:", r2.json()["name"])

        # 2. 获取分组聚合统计
        r3 = client.get("/api/groups")
        assert r3.status_code == 200
        groups = r3.json()
        print("[OK] [3/4] 成功拉取环境分组聚合概览:")
        for g in groups:
            print(f"      - 分组名称: {g['name']} | 节点总数: {g['total']} | 健康: {g['healthy']} | 异常: {g['down']}")

        # 3. 测试按指定分组筛选接口
        r4 = client.get("/api/targets?group=测试环境")
        assert r4.status_code == 200
        qa_targets = r4.json()
        assert len(qa_targets) >= 1
        assert all(t["group_name"] == "测试环境" for t in qa_targets)
        print(f"[OK] [4/4] 成功按【测试环境】精准过滤出 {len(qa_targets)} 个目标，隔离正常！")

    print("\n>>> 多环境分组能力全流程自测 100% 成功跑通！<<<\n")

if __name__ == "__main__":
    test_group_features()
