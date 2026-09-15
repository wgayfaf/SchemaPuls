import os
import sys
import json
from fastapi.testclient import TestClient

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")
sys.path.insert(0, backend_dir)

from app.main import app
from app.database import engine, init_db
from sqlmodel import Session, select
from app.models import MachineNode, ApiProbe, Environment, ServiceGroup
from app.services.action_engine import (
    execute_pre_actions,
    execute_post_actions,
    get_nested_value
)

def test_action_engine_unit():
    print("==================================================")
    print("   1. 测试前置操作与后置操作内核 (ActionEngine)")
    print("==================================================")
    
    # 1.1 测试前置操作
    pre_actions = [
        {"enabled": True, "type": "set_variable", "key": "app_ver", "value": "v2.0.1"},
        {"enabled": True, "type": "set_variable", "key": "dyn_ts", "value": "{{$timestamp}}"},
        {"enabled": True, "type": "inject_header", "key": "X-Custom-Client", "value": "SchemaPulse_{{app_ver}}"},
        {"enabled": True, "type": "inject_param", "key": "ts", "value": "{{dyn_ts}}"},
        {"enabled": True, "type": "custom_script", "key": "", "value": "variables['sign'] = 'SIGN_' + variables['app_ver']"}
    ]
    headers, params, body, path, vars_out = execute_pre_actions(
        pre_actions=pre_actions,
        headers={"Accept": "application/json"},
        params={"page": "1"},
        body='{"version": "{{app_ver}}", "sign": "{{sign}}"}',
        path="/api/{{app_ver}}/users",
        auth_token="token_xyz"
    )
    
    assert vars_out["app_ver"] == "v2.0.1"
    assert vars_out["sign"] == "SIGN_v2.0.1"
    assert headers["X-Custom-Client"] == "SchemaPulse_v2.0.1"
    assert "ts" in params
    assert path == "/api/v2.0.1/users"
    assert '"version": "v2.0.1"' in body
    assert '"sign": "SIGN_v2.0.1"' in body
    print(f"[OK] 前置操作与变量多层渲染通过: headers={headers}, params={params}, path={path}, sign={vars_out['sign']}")

    # 1.2 测试嵌套路径提取
    data = {
        "code": 200,
        "message": "success",
        "data": {
            "token": "tok_998877",
            "user": {
                "id": 1001,
                "name": "Alice",
                "roles": ["admin", "tester"]
            }
        }
    }
    f1, v1 = get_nested_value(data, "code")
    assert f1 and v1 == 200
    f2, v2 = get_nested_value(data, "data.user.id")
    assert f2 and v2 == 1001
    f3, v3 = get_nested_value(data, "data.user.roles[1]")
    assert f3 and v3 == "tester"
    print(f"[OK] 嵌套数据提取测试通过: code={v1}, user.id={v2}, role[1]={v3}")

    # 1.3 测试后置操作断言与提取
    post_actions = [
        {"enabled": True, "name": "状态码为200", "type": "assert_status_code", "operator": "equals", "target_value": "200"},
        {"enabled": True, "name": "耗时小于1000ms", "type": "assert_latency", "operator": "less_than", "target_value": "1000"},
        {"enabled": True, "name": "code为200", "type": "assert_json_path", "expression": "code", "operator": "equals", "target_value": "200"},
        {"enabled": True, "name": "用户名称为Alice", "type": "assert_json_path", "expression": "data.user.name", "operator": "equals", "target_value": "Alice"},
        {"enabled": True, "name": "响应包含success", "type": "assert_body_contains", "operator": "contains", "target_value": "success"},
        {"enabled": True, "name": "提取Token", "type": "extract_variable", "expression": "data.token", "target_value": "extractedToken"}
    ]
    all_passed, results, extracted = execute_post_actions(
        post_actions=post_actions,
        status_code=200,
        latency_ms=120.5,
        response_headers={"content-type": "application/json; charset=utf-8"},
        response_data=data,
        context_variables=vars_out
    )
    assert all_passed is True
    assert len(results) == 6
    assert extracted.get("extractedToken") == "tok_998877"
    for r in results:
        assert r["passed"] is True, f"断言失败: {r}"
    print(f"[OK] 后置操作断言全部通过，成功提取变量: {extracted}")

    # 1.4 测试断言失败检测
    fail_actions = [
        {"enabled": True, "name": "状态码应为500", "type": "assert_status_code", "operator": "equals", "target_value": "500"},
        {"enabled": True, "name": "耗时超速断言", "type": "assert_latency", "operator": "less_than", "target_value": "50"}
    ]
    fail_passed, fail_res, _ = execute_post_actions(
        post_actions=fail_actions,
        status_code=200,
        latency_ms=120.5,
        response_data=data
    )
    assert fail_passed is False
    assert fail_res[0]["passed"] is False
    assert fail_res[1]["passed"] is False
    print(f"[OK] 断言异常捕获机制验证通过: fail_passed={fail_passed}")


def test_api_test_run_with_actions():
    print("\n==================================================")
    print("   2. 测试 API 在线调试端点 (/api/apis/test-run)")
    print("==================================================")
    init_db()
    client = TestClient(app)

    with Session(engine) as session:
        env = session.exec(select(Environment)).first()
        if not env:
            env = Environment(name="测试环境", order_num=1)
            session.add(env)
            session.commit()
            session.refresh(env)

        grp = session.exec(select(ServiceGroup).where(ServiceGroup.environment_id == env.id)).first()
        if not grp:
            grp = ServiceGroup(environment_id=env.id, name="测试集群")
            session.add(grp)
            session.commit()
            session.refresh(grp)

        machine = session.exec(select(MachineNode).where(MachineNode.host == "httpbin.org")).first()
        if not machine:
            machine = MachineNode(
                group_id=grp.id,
                name="HttpBin节点",
                host="httpbin.org",
                port=80,
                is_active=True
            )
            session.add(machine)
            session.commit()
            session.refresh(machine)
        m_id = machine.id

    # 调试测试：前置操作注入请求头与参数，后置操作断言状态码
    payload = {
        "machine_id": m_id,
        "http_method": "GET",
        "http_path": "/get",
        "http_params": [
            {"enabled": True, "key": "client", "value": "{{my_app}}"}
        ],
        "http_headers": [
            {"enabled": True, "key": "X-Client-Trace", "value": "{{$uuid}}"}
        ],
        "pre_actions": [
            {"enabled": True, "type": "set_variable", "key": "my_app", "value": "SchemaPulseTest"},
            {"enabled": True, "type": "inject_header", "key": "X-Pre-Header", "value": "PreValue_{{my_app}}"}
        ],
        "post_actions": [
            {"enabled": True, "name": "HTTP 状态码等于 200", "type": "assert_status_code", "operator": "equals", "target_value": "200"},
            {"enabled": True, "name": "HTTP 状态码在 2xx 范围", "type": "assert_status_code", "operator": "in_2xx", "target_value": ""},
            {"enabled": True, "name": "耗时小于 10000ms", "type": "assert_latency", "operator": "less_than", "target_value": "10000"}
        ]
    }

    res = client.post("/api/apis/test-run", json=payload)
    assert res.status_code == 200, f"test-run 返回错误: {res.text}"
    data = res.json()
    assert "assertions_summary" in data
    assert "assertions_result" in data
    assert "rendered_headers" in data
    assert data["rendered_headers"].get("X-Pre-Header") == "PreValue_SchemaPulseTest"
    assert data["rendered_params"].get("client") == "SchemaPulseTest"
    print(f"[OK] /api/apis/test-run 执行完成:")
    print(f"     状态码: {data['status_code']}, 断言总数: {data['assertions_summary']['total']}, 通过数: {data['assertions_summary']['passed_count']}")
    print(f"     渲染后 Headers: {data['rendered_headers']}")
    print(f"     渲染后 Params: {data['rendered_params']}")


def test_api_crud_and_persistence():
    print("\n==================================================")
    print("   3. 测试接口探针创建/读取/更新的持久化 (/api/apis)")
    print("==================================================")
    client = TestClient(app)
    with Session(engine) as session:
        machine = session.exec(select(MachineNode)).first()
        m_id = machine.id

    create_payload = {
        "machine_id": m_id,
        "name": "用户订单服务探针_测试",
        "http_path": "/get",
        "http_method": "GET",
        "expected_schema": {"type": "object"},
        "pre_actions": [
            {"enabled": True, "type": "set_variable", "key": "trace_seed", "value": "{{$uuid}}"},
            {"enabled": True, "type": "inject_header", "key": "X-Trace-Id", "value": "{{trace_seed}}"}
        ],
        "post_actions": [
            {"enabled": True, "name": "状态码200", "type": "assert_status_code", "operator": "equals", "target_value": "200"},
            {"enabled": True, "name": "响应小于2000ms", "type": "assert_latency", "operator": "less_than", "target_value": "2000"}
        ]
    }
    
    # 1. 创建接口
    c_res = client.post("/api/apis", json=create_payload)
    assert c_res.status_code == 200, f"创建失败: {c_res.text}"
    created_api = c_res.json()
    api_id = created_api["id"]
    assert len(created_api["pre_actions"]) == 2
    assert len(created_api["post_actions"]) == 2
    print(f"[OK] 接口创建成功, ID={api_id}, pre_actions={len(created_api['pre_actions'])}, post_actions={len(created_api['post_actions'])}")

    # 2. 读取列表验证回显
    l_res = client.get(f"/api/apis?machine_id={m_id}")
    assert l_res.status_code == 200
    apis = l_res.json()
    matched = next((a for a in apis if a["id"] == api_id), None)
    assert matched is not None
    assert matched["pre_actions"][0]["key"] == "trace_seed"
    assert matched["post_actions"][0]["target_value"] == "200"
    print(f"[OK] 列表读取回显一致: pre_actions[0].key={matched['pre_actions'][0]['key']}")

    # 3. 更新接口
    update_payload = dict(create_payload)
    update_payload["name"] = "用户订单服务探针_修改版"
    update_payload["post_actions"].append({
        "enabled": True,
        "name": "响应文本包含OK",
        "type": "assert_body_contains",
        "operator": "contains",
        "target_value": "OK"
    })
    u_res = client.put(f"/api/apis/{api_id}", json=update_payload)
    assert u_res.status_code == 200
    updated_api = u_res.json()
    assert updated_api["name"] == "用户订单服务探针_修改版"
    assert len(updated_api["post_actions"]) == 3
    print(f"[OK] 接口更新成功, post_actions 增至 {len(updated_api['post_actions'])} 条")

    # 4. 清理测试接口
    d_res = client.delete(f"/api/apis/{api_id}")
    assert d_res.status_code == 200
    print(f"[OK] 清理测试接口完成")


if __name__ == "__main__":
    test_action_engine_unit()
    test_api_test_run_with_actions()
    test_api_crud_and_persistence()
    print("\n==================================================")
    print("🎉🎉 全部前置操作与后置操作测试 100% 通过！ 🎉🎉")
    print("==================================================")
