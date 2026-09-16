import sys
import os
import json
import asyncio
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath("backend"))

from sqlmodel import Session, select
from app.database import engine
from app.models import MachineNode, ApiProbe, Environment, ServiceGroup
from app.main import ApiTestRunPayload, test_run_api

async def test_debug_endpoint():
    print("=== 测试 /api/apis/test-run 真实逻辑 ===")
    with Session(engine) as db:
        machine = db.exec(select(MachineNode)).first()
        probe = db.exec(select(ApiProbe).where(ApiProbe.http_path == "/api/table/table-manager/detail/{tableId}")).first()
        assert machine is not None and probe is not None
        
        # 构造请求体
        req_data = ApiTestRunPayload(
            machine_id=machine.id,
            http_method=probe.http_method,
            http_path=probe.http_path,
            http_params=probe.http_params,
            http_headers=probe.http_headers,
            http_body_type=probe.http_body_type,
            http_body=probe.http_body,
            auth_type=probe.auth_type,
            auth_config=probe.auth_config,
            pre_actions=probe.pre_actions,
            post_actions=probe.post_actions,
            expected_schema=probe.expected_schema
        )
        
        # Mock check_http_detailed 捕获发出的实际 url 和 headers
        with patch("app.services.probe_service.check_http_detailed") as mock_check:
            async def fake_check(url, method, headers, params, body, body_type):
                print(f"Captured Target URL: {url}")
                print(f"Captured Target Headers: {headers}")
                print(f"Captured Target Params: {params}")
                return True, 200, 45, {"code": 0, "msg": "ok", "data": {"id": "tbl_Hy"}}, None, {}, '{"code":0}'
            
            mock_check.side_effect = fake_check
            
            # 运行 test_run_api
            resp = await test_run_api(req_data, db)
            print("Response:", json.dumps(resp, ensure_ascii=False))
            
            # 断言 mock_check 收到的参数
            args, kwargs = mock_check.call_args
            called_url = args[0] if args else kwargs.get("url")
            called_headers = kwargs.get("headers")
            called_params = kwargs.get("params")
            
            # 1. 验证 URL 中路径参数已被替换为 tbl_Hy
            assert "/api/table/table-manager/detail/tbl_Hy" in called_url, f"Expected URL to have tbl_Hy, got {called_url}"
            # 2. 验证 params 为空或没有 tableId
            assert called_params is None or "tableId" not in called_params, f"tableId should not be in params: {called_params}"
            # 3. 验证 headers 中包含 Authorization
            assert "Authorization" in called_headers, f"Authorization header missing in {called_headers}"
            
            print(">>> /api/apis/test-run 发包测试全部通过！")

if __name__ == "__main__":
    asyncio.run(test_debug_endpoint())
