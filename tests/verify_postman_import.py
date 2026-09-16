import os
import sys
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
from fastapi.testclient import TestClient
from sqlmodel import Session, select

# 确保导入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app
from app.database import engine
from app.models import MachineNode, ServiceGroup, Environment, ApiProbe

client = TestClient(app)

def test_postman_import_end_to_end():
    print("==================================================")
    print("   1. 测试 Postman 真实数据包解析 (table.zip)")
    print("==================================================")
    zip_path = os.path.join(os.path.dirname(__file__), "..", "table.zip")
    assert os.path.exists(zip_path), f"找不到测试文件: {zip_path}"
    
    with Session(engine) as db:
        # 获取或创建一个测试宿主环境与机器
        env = db.exec(select(Environment).where(Environment.name == "导入测试环境")).first()
        if not env:
            env = Environment(name="导入测试环境", description="测试Postman导入")
            db.add(env)
            db.commit()
            db.refresh(env)
            
        group = db.exec(select(ServiceGroup).where(ServiceGroup.name == "导入测试分组")).first()
        if not group:
            group = ServiceGroup(name="导入测试分组", environment_id=env.id)
            db.add(group)
            db.commit()
            db.refresh(group)
            
        machine = db.exec(select(MachineNode).where(MachineNode.name == "导入测试宿主机")).first()
        if not machine:
            machine = MachineNode(
                group_id=group.id,
                name="导入测试宿主机",
                host="prod-cn.your-api-server.com",
                port=80,
                base_url=None # 初始为空，测试自动从 Postman 环境继承
            )
            db.add(machine)
            db.commit()
            db.refresh(machine)
            
        m_id = machine.id
        
    print(f"[OK] 准备测试机器节点: ID={m_id}, Name=导入测试宿主机")

    # 1. 测试 /preview 端点
    with open(zip_path, "rb") as f:
        resp = client.post(
            f"/api/machines/{m_id}/import-postman/preview",
            files={"file": ("table.zip", f, "application/zip")}
        )
    assert resp.status_code == 200, f"Preview 失败: {resp.text}"
    preview_res = resp.json()
    assert preview_res["success"] is True
    data = preview_res["data"]
    
    print(f"[OK] 成功解析 Postman 集合: {data.get('collection_name')}")
    print(f"[OK] 提取到 Postman 环境变量: {data.get('environment_variables')}")
    print(f"[OK] 提取到 Base URL: {data.get('base_url')}")
    assert data.get("base_url") == "http://prod-cn.your-api-server.com"
    
    apis = data.get("apis", [])
    print(f"[OK] 解析出接口数量: {len(apis)}")
    assert len(apis) >= 1
    login_api = apis[0]
    print(f"     接口名称: {login_api['name']}")
    print(f"     请求方式: {login_api['http_method']}")
    print(f"     相对路径: {login_api['http_path']}")
    assert login_api['http_method'] == "POST"
    assert login_api['http_path'] == "/api/auth/acc/email/login"
    assert len(login_api['pre_actions']) >= 1
    assert "jsrsasign" in login_api['pre_actions'][0]['value']
    assert len(login_api['post_actions']) >= 1
    assert "accessToken" in login_api['post_actions'][0]['value']
    print("[OK] 前置 RSA 脚本与后置 Token 提取断言脚本均成功无损转换！")

    # 2. 测试 /confirm 批量入库
    confirm_payload = {
        "selected_apis": apis,
        "environment_variables": data.get("environment_variables", {}),
        "postman_base_url": data.get("base_url"),
        "sync_env_vars": True,
        "update_machine_base_url": True,
        "conflict_policy": "overwrite",
        "cron_interval_minutes": 5
    }
    confirm_resp = client.post(
        f"/api/machines/{m_id}/import-postman/confirm",
        json=confirm_payload
    )
    assert confirm_resp.status_code == 200, f"Confirm 失败: {confirm_resp.text}"
    confirm_res = confirm_resp.json()
    print("[OK] 导入确认返回:", json.dumps(confirm_res, ensure_ascii=False, indent=2))
    assert confirm_res["success"] is True
    res_info = confirm_res["result"]
    assert res_info["total_imported"] >= 1
    assert res_info["updated_machine_base_url"] is True

    # 3. 校验数据库中的持久化数据
    with Session(engine) as db:
        m = db.get(MachineNode, m_id)
        assert m.base_url == "http://prod-cn.your-api-server.com"
        print(f"[OK] 宿主机器 base_url 成功自动同步为: {m.base_url}")
        
        # 校验所属环境的变量池
        g = db.get(ServiceGroup, m.group_id)
        e = db.get(Environment, g.environment_id)
        assert "baseUrl" in (e.variables or {})
        print(f"[OK] 环境持久化变量池已写入: {e.variables}")
        
        # 校验接口列表
        probe_list = db.exec(select(ApiProbe).where(ApiProbe.machine_id == m_id)).all()
        assert len(probe_list) >= 1
        imported_probe = probe_list[0]
        print(f"[OK] 数据库中已成功挂载接口探针: ID={imported_probe.id}, Name={imported_probe.name}, Path={imported_probe.http_path}")
        assert imported_probe.http_path == "/api/auth/acc/email/login"
        assert imported_probe.http_method == "POST"

        # 清理测试数据
        for p in probe_list:
            db.delete(p)
        db.delete(m)
        db.delete(g)
        db.delete(e)
        db.commit()
        print("[OK] 测试数据清理完成！")

    print("\n==================================================")
    print("🎉 Postman 格式数据解析与机器关联批量导入端到端验证 100% 通过！")
    print("==================================================")

if __name__ == "__main__":
    test_postman_import_end_to_end()
