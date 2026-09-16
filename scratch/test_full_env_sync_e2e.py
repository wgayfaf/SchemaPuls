import os
import sys
import time
import requests
from sqlmodel import Session, select, create_engine

sys.path.insert(0, os.path.abspath("backend"))
from app.models import Environment, ServiceGroup, MachineNode, ApiProbe

def main():
    print("=== 1. Testing API Test-Run Environment Sync ===")
    engine = create_engine("sqlite:///backend/monitor.db")
    
    # 查找一台测试机器
    with Session(engine) as session:
        m = session.exec(select(MachineNode)).first()
        assert m is not None, "No MachineNode found in DB"
        machine_id = m.id
        grp = session.get(ServiceGroup, m.group_id)
        env = session.get(Environment, grp.environment_id)
        env_id = env.id
        print(f"Target Machine ID: {machine_id}, Env ID: {env_id} ({env.name})")

    # 构造包含多种前置操作与后置操作的 test-run 请求
    payload = {
        "machine_id": machine_id,
        "http_method": "GET",
        "http_path": "/api/test_sync",
        "http_params": [],
        "http_headers": [],
        "http_body_type": "none",
        "auth_type": "none",
        "pre_actions": [
            {"enabled": True, "type": "set_variable", "key": "SYNC_PRE_FORM", "value": "val_pre_form"},
            {"enabled": True, "type": "javascript", "value": 'pm.variables.set("SYNC_PRE_JS", "val_pre_js");'}
        ],
        "post_actions": [
            {"enabled": True, "type": "extract_variable", "key": "SYNC_POST_EXTRACT", "expression": "data.id"},
            {"enabled": True, "type": "javascript", "value": 'pm.variables.set("SYNC_POST_JS", "val_post_js");'}
        ]
    }

    # 调用 /api/apis/test-run
    res = requests.post("http://127.0.0.1:8000/api/apis/test-run", json=payload)
    print("Test-run response status:", res.status_code)
    data = res.json()
    updated_vars = data.get("environment", {}).get("updated_variables", {})
    print("Test-run updated_variables:", updated_vars)
    
    assert "SYNC_PRE_FORM" in updated_vars, "SYNC_PRE_FORM missing in updated_variables!"
    assert "SYNC_PRE_JS" in updated_vars, "SYNC_PRE_JS missing in updated_variables!"
    assert "SYNC_POST_JS" in updated_vars, "SYNC_POST_JS missing in updated_variables!"
    print("--> Test-run returned variables checked successfully!")

    # 验证数据库落盘
    with Session(engine) as session:
        env_db = session.get(Environment, env_id)
        vars_db = env_db.variables or {}
        print("DB Environment.variables:", vars_db)
        assert vars_db.get("SYNC_PRE_FORM") == "val_pre_form", "DB missing SYNC_PRE_FORM"
        assert vars_db.get("SYNC_PRE_JS") == "val_pre_js", "DB missing SYNC_PRE_JS"
        assert vars_db.get("SYNC_POST_JS") == "val_post_js", "DB missing SYNC_POST_JS"
    print("--> Database persistence checked successfully!")

    # 验证 GET /api/environments/{id}/variables 接口
    env_res = requests.get(f"http://127.0.0.1:8000/api/environments/{env_id}/variables")
    assert env_res.status_code == 200
    api_vars = env_res.json().get("variables", {})
    assert api_vars.get("SYNC_PRE_FORM") == "val_pre_form"
    assert api_vars.get("SYNC_PRE_JS") == "val_pre_js"
    assert api_vars.get("SYNC_POST_JS") == "val_post_js"
    print("--> API GET variables checked successfully!")

    print("\n=== ALL BACKEND ENVIRONMENT SYNC CHECKS PASSED 100%! ===")

if __name__ == "__main__":
    main()
