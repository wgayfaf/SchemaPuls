import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")
sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

def test_api_metrics_isolation():
    print("==================================================")
    print("   SchemaPulse - 机器接口专属时序与历史隔离测试")
    print("==================================================")

    with TestClient(app) as client:
        # 1. 验证不存在接口的 404 严谨性 (禁止跨表回退)
        r_non_exist = client.get("/api/apis/999999/history")
        assert r_non_exist.status_code == 404, f"Expected 404, got {r_non_exist.status_code}"
        print("[OK] [1/4] 不存在的接口 (/api/apis/999999/history) 正确返回 404，已杜绝跨表 fallback 污染！")

        # 2. 创建一个全新的测试接口
        create_res = client.post("/api/apis", json={
            "machine_id": 1,
            "name": "自动化测试专用隔离接口",
            "http_path": "/test-isolation",
            "http_method": "GET",
            "cron_interval_minutes": 5,
            "expected_schema": {"type": "object"},
            "is_active": True,
            "email_receivers": []
        })
        assert create_res.status_code == 200, f"Create API failed: {create_res.text}"
        new_api = create_res.json()
        new_api_id = new_api["id"]
        print(f"[OK] [2/4] 成功创建新接口: ID={new_api_id}, Name={new_api['name']}")

        try:
            # 3. 验证新建接口在无探测流水时，严格返回 0 条流水 (彻底解决'都显示老数据'的问题)
            hist_res = client.get(f"/api/apis/{new_api_id}/history")
            assert hist_res.status_code == 200
            hist_data = hist_res.json()
            assert len(hist_data) == 0, f"新建接口应为 0 条历史，却返回了 {len(hist_data)} 条（存在历史数据污染！）"
            print(f"[OK] [3/4] 新建接口历史流水严格为空 (共 {len(hist_data)} 条)，未被老数据或其它接口污染！")

            metrics_res = client.get(f"/api/apis/{new_api_id}/metrics")
            assert metrics_res.status_code == 200
            metrics_data = metrics_res.json()
            assert metrics_data["api_id"] == new_api_id
            assert len(metrics_data["points"]) == 0
            print(f"      - 时序点位数组严格为空 (共 {len(metrics_data['points'])} 个绘图点)")

            # 4. 对该新接口触发一次拨测，验证只精准生成属于它自身的专属流水
            trigger_res = client.post(f"/api/apis/{new_api_id}/trigger")
            assert trigger_res.status_code == 200
            
            hist_after = client.get(f"/api/apis/{new_api_id}/history").json()
            assert len(hist_after) >= 1, "应至少有 1 条专属流水"
            assert all(h["api_probe_id"] == new_api_id for h in hist_after), "所有历史流水必须严格属于当前新建接口自身！"
            assert hist_after[0]["api_name"] == "自动化测试专用隔离接口"
            print(f"[OK] [4/4] 拨测后精准返回属于该接口自身的专属探测记录 (共 {len(hist_after)} 条):")
            print(f"      - 记录 ID: {hist_after[0]['id']}")
            print(f"      - 接口名称: {hist_after[0]['api_name']}")
            print(f"      - 专属关联 api_probe_id: {hist_after[0]['api_probe_id']}")
            print(f"      - 所属宿主机: {hist_after[0]['machine_name']}")

            metrics_after = client.get(f"/api/apis/{new_api_id}/metrics").json()
            assert len(metrics_after["points"]) == len(hist_after)
            print(f"      - 专属时序点位同步更新为 {len(metrics_after['points'])} 个绘图点")

        finally:
            # 清理测试接口
            del_res = client.delete(f"/api/apis/{new_api_id}")
            assert del_res.status_code == 200
            # 确认级联删除彻底清理了该接口的历史数据
            orphan_check = client.get(f"/api/apis/{new_api_id}/history")
            assert orphan_check.status_code == 404
            print(f"[Clean] 测试接口 ID={new_api_id} 已安全清理，级联历史已彻底清除。")

    print("\n>>> 机器接口专属时序与历史隔离测试 100% 验证通过！<<<")

if __name__ == "__main__":
    test_api_metrics_isolation()
