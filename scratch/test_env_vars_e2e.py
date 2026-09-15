import sys
import os
import asyncio

# 添加 backend 到 sys.path
sys.path.insert(0, os.path.abspath("backend"))

from sqlmodel import Session, select
from app.database import engine, init_db
from app.models import Environment, ServiceGroup, MachineNode, ApiProbe
from app.services.action_engine import execute_pre_actions, execute_post_actions


def test_chain_environment_variables():
    init_db()
    with Session(engine) as session:
        # 1. 获取或创建测试环境
        env = session.exec(select(Environment).where(Environment.name == "自动化测试环境")).first()
        if not env:
            env = Environment(name="自动化测试环境", description="测试环境变量持久化", variables={"EXISTING_VAR": "hello_world"})
            session.add(env)
            session.commit()
            session.refresh(env)
        else:
            env.variables = {"EXISTING_VAR": "hello_world"}
            session.add(env)
            session.commit()
            session.refresh(env)

        # 2. 模拟接口 A (登录接口) 的后置脚本: pm.environment.set("JWT_TOKEN", "mocked_jwt_token_999")
        post_actions_a = [
            {
                "type": "javascript",
                "enabled": True,
                "value": """
                pm.test("登录成功", function() {
                    pm.expect(pm.response.code).to.equal(200);
                });
                var data = pm.response.json();
                pm.environment.set("JWT_TOKEN", data.token);
                pm.environment.set("USER_ID", data.user_id);
                """
            }
        ]

        all_passed, asserts, extracted, updated_env = execute_post_actions(
            post_actions=post_actions_a,
            status_code=200,
            latency_ms=45.0,
            response_data={"code": 0, "token": "mocked_jwt_token_999", "user_id": 10086},
            environment_variables=env.variables
        )

        print("--- 接口 A 后置动作执行 ---")
        print("断言通过状态:", all_passed)
        print("断言详情:", asserts)
        print("提取的环境变量更新:", updated_env)
        assert updated_env.get("JWT_TOKEN") == "mocked_jwt_token_999", f"JWT_TOKEN 未正确提取: {updated_env}"
        assert updated_env.get("USER_ID") == 10086, f"USER_ID 未正确提取: {updated_env}"

        # 模拟持久化写回环境
        curr_vars = dict(env.variables or {})
        curr_vars.update(updated_env)
        env.variables = curr_vars
        session.add(env)
        session.commit()
        session.refresh(env)

        print("\n--- 数据库 Environment 变量池 ---")
        print(env.variables)
        assert env.variables.get("JWT_TOKEN") == "mocked_jwt_token_999"

        # 3. 模拟接口 B (业务探测接口): 请求头包含 Authorization: Bearer {{JWT_TOKEN}}，body 包含 {"uid": "{{USER_ID}}"}
        headers_b = {"Authorization": "Bearer {{JWT_TOKEN}}", "Content-Type": "application/json"}
        params_b = {"token_check": "{{JWT_TOKEN}}"}
        body_b = '{"user_id": {{USER_ID}}, "auth": "{{JWT_TOKEN}}"}'
        path_b = "/api/v1/user/{{USER_ID}}"

        final_headers, final_params, final_body, final_path, variables, pre_updated_env = execute_pre_actions(
            pre_actions=[],
            headers=headers_b,
            params=params_b,
            body=body_b,
            path=path_b,
            environment_variables=env.variables
        )

        print("\n--- 接口 B 前置变量解析渲染 ---")
        print("渲染后 Header:", final_headers)
        print("渲染后 Params:", final_params)
        print("渲染后 Body:", final_body)
        print("渲染后 Path:", final_path)

        assert final_headers["Authorization"] == "Bearer mocked_jwt_token_999"
        assert final_params["token_check"] == "mocked_jwt_token_999"
        assert '"user_id": 10086' in final_body
        assert '"auth": "mocked_jwt_token_999"' in final_body
        assert final_path == "/api/v1/user/10086"
        print("\n[SUCCESS] 端到端环境变量持久化与跨接口直接调用验证完美通过！".encode("gbk", errors="ignore").decode("gbk"))


if __name__ == "__main__":
    test_chain_environment_variables()
