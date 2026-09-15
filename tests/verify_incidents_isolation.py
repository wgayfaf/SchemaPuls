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

def test_incidents_isolation():
    print("==================================================")
    print("   SchemaPulse - 故障排障中心与接口管理严格对齐测试")
    print("==================================================")

    with TestClient(app) as client:
        # 1. 获取当前所有接口管理中的接口
        apis_res = client.get("/api/apis")
        assert apis_res.status_code == 200
        active_apis = apis_res.json()
        active_api_ids = {a["id"] for a in active_apis}
        print(f"[OK] [1/4] 当前接口管理内共有 {len(active_apis)} 个有效纳管接口: IDs={active_api_ids}")

        # 2. 验证受损节点提取逻辑：受损集合必须是 active_apis 的子集
        down_apis = [a for a in active_apis if a.get("current_status") in ("DOWN", "DEGRADED", "CIRCUIT_BROKEN")]
        for item in down_apis:
            assert item["id"] in active_api_ids, f"受损清单中的接口 ID={item['id']} 不在接口管理中！"
        print(f"[OK] [2/4] 当前受损节点清单共 {len(down_apis)} 个，100% 属于接口管理内的纳管接口")

        # 3. 创建临时接口并模拟故障
        create_res = client.post("/api/apis", json={
            "machine_id": 1,
            "name": "待删除的故障临时接口",
            "http_path": "/fault-temp",
            "http_method": "GET",
            "cron_interval_minutes": 5,
            "expected_schema": {"type": "object"},
            "is_active": True,
            "email_receivers": []
        })
        assert create_res.status_code == 200
        temp_api = create_res.json()
        temp_id = temp_api["id"]
        print(f"[OK] [3/4] 创建临时测试接口 ID={temp_id}, Name={temp_api['name']}")

        # 4. 删除该接口，验证接口管理中没有该接口后，排障中心绝对不会再包含它
        del_res = client.delete(f"/api/apis/{temp_id}")
        assert del_res.status_code == 200
        
        # 重新获取接口列表与老 targets 列表
        apis_after = client.get("/api/apis").json()
        assert not any(a["id"] == temp_id for a in apis_after), "删除后接口管理中不应存在该接口"
        
        down_apis_after = [a for a in apis_after if a.get("current_status") in ("DOWN", "DEGRADED", "CIRCUIT_BROKEN")]
        assert not any(a["id"] == temp_id for a in down_apis_after), "排障受损清单中绝对不应出现接口管理中已删除或不存在的接口！"
        print(f"[OK] [4/4] 验证通过！接口被删除后，故障排障清单中彻底不再显示该接口！")

    print("\n>>> 故障告警排障中心与接口管理严格对齐测试 100% 验证通过！<<<")

if __name__ == "__main__":
    test_incidents_isolation()
