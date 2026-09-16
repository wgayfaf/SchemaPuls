import sys
import os
import json
import asyncio
from unittest.mock import patch

sys.path.insert(0, os.path.abspath("backend"))

from sqlmodel import Session, select
from app.database import engine
from app.models import MachineNode, ApiProbe, Environment, ServiceGroup
from app.services.postman_importer import parse_postman_package, import_postman_to_machine
from app.main import ApiTestRunPayload, test_run_api

user_login_json = """{
    "info": {
        "name": "table",
        "description": "",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [
        {
            "name": "auth",
            "description": "",
            "item": [
                {
                    "name": "login",
                    "description": "",
                    "item": [
                        {
                            "name": "邮箱登录",
                            "description": "",
                            "event": [
                                {
                                    "listen": "prerequest",
                                    "script": {
                                        "exec": [
                                            "const jsrsasign = require('jsrsasign');",
                                            "let publicKeyPEM = 'MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAy7YbsS0zH21A27PccrK99ee43Xf1hLlrmw3tO8U2DmO/mbc8mL/lMjN8u4k3eHzGETb1kRJfqbNSEugQkrskTHOJctl0VEbobY9JS3CBi0WxeALmoh4Rlaao2LllE85vPli2w3sGtia9rbsqJtFTW+KfcrutXJVJ+vGRqB9F31gQscNkZoo2uu5RjuGn5P83bu52nn9stikg9uuoIH/gZD8jIEgCnNWDAlmQCQH27BjaJuf6JNMPcvTQAHJDINmwJj7xCWd03k+dseT3vrFV6WTI7aEo9AAoEOhoPg/JCKNSWGJutW7pfkJh9SdUltpQIc+guU7YQaTJ8n8I+7i3YwIDAQAB';",
                                            "publicKeyPEM = \\"-----BEGIN PUBLIC KEY-----\\"+ publicKeyPEM + \\"-----END PUBLIC KEY-----\\";",
                                            "const plainPassword = \\"1qaz2wsx\\";",
                                            "const pubKeyObj = jsrsasign.KEYUTIL.getKey(publicKeyPEM);",
                                            "const encryptedHex = jsrsasign.KJUR.crypto.Cipher.encrypt(plainPassword, pubKeyObj);",
                                            "function hexToBase64(hexString) {",
                                            "    const bytes = new Uint8Array(hexString.length / 2);",
                                            "    for (let i = 0; i < hexString.length; i += 2) {",
                                            "        bytes[i / 2] = parseInt(hexString.substr(i, 2), 16);",
                                            "    }",
                                            "    return btoa(String.fromCharCode.apply(null, bytes));",
                                            "}",
                                            "const encryptedBase64 = hexToBase64(encryptedHex);",
                                            "pm.environment.set(\\"ENCRYPTED_PASSWORD\\", JSON.stringify(encryptedBase64));"
                                        ],
                                        "type": "text/javascript",
                                        "packages": {}
                                    }
                                },
                                {
                                    "listen": "test",
                                    "script": {
                                        "exec": [
                                            "const res = pm.response.json();",
                                            "// 检查请求是否成功",
                                            "if (res.code === 0 && res.data && res.data.accessToken) {",
                                            "    // 将 accessToken 写入当前环境变量",
                                            "    pm.environment.set(\\"token\\", res.data.accessToken);",
                                            "    console.log(\\"Token 已保存:\\", res.data.accessToken);",
                                            "} else {",
                                            "    console.log(\\"登录失败或未获取到 token\\");",
                                            "}"
                                        ],
                                        "type": "text/javascript",
                                        "packages": {}
                                    }
                                }
                            ],
                            "auth": {},
                            "request": {
                                "auth": {
                                    "type": "noauth",
                                    "noauth": []
                                },
                                "method": "POST",
                                "body": {
                                    "mode": "raw",
                                    "raw": "{\\r\\n  \\"email\\": \\"wuyu@chubbycenter.com\\",\\r\\n  \\"password\\": {{ENCRYPTED_PASSWORD}}\\r\\n}",
                                    "options": {
                                        "raw": {
                                            "language": "json"
                                        }
                                    }
                                },
                                "header": [],
                                "url": {
                                    "raw": "{{baseUrl}}/api/auth/acc/email/login",
                                    "path": [
                                        "api",
                                        "auth",
                                        "acc",
                                        "email",
                                        "login"
                                    ],
                                    "host": [
                                        "{{baseUrl}}"
                                    ],
                                    "query": [],
                                    "variable": []
                                }
                            },
                            "response": []
                        }
                    ]
                }
            ]
        }
    ]
}"""

async def test_all():
    print("=== 1. 解析导入数据 ===")
    parsed = parse_postman_package(user_login_json.encode('utf-8'), "login.json")
    apis = parsed["apis"]
    assert len(apis) == 1
    api = apis[0]
    print(f"API Name: {api['name']}")
    print(f"Pre actions count: {len(api['pre_actions'])}")
    print(f"Post actions count: {len(api['post_actions'])}")
    assert len(api['post_actions']) == 1
    assert api['post_actions'][0]['type'] == 'javascript'
    assert 'pm.environment.set("token"' in api['post_actions'][0]['value']
    print(">>> 1. 解析成功且包含后置 JS 脚本！")

    print("\n=== 2. 持久化落库到机器 1 ===")
    with Session(engine) as db:
        machine = db.exec(select(MachineNode)).first()
        assert machine is not None
        res = import_postman_to_machine(
            db=db,
            machine_id=machine.id,
            selected_apis=apis,
            conflict_policy="overwrite"
        )
        print("Import result:", res)
        probe = db.exec(select(ApiProbe).where(ApiProbe.machine_id == machine.id, ApiProbe.name == api['name'])).first()
        assert probe is not None
        print(f"Probe ID: {probe.id}, name: {probe.name}")
        print(f"Probe Post actions count: {len(probe.post_actions)}")
        assert len(probe.post_actions) == 1
        assert probe.post_actions[0]['type'] == 'javascript'
        assert 'pm.environment.set("token"' in probe.post_actions[0]['value']
        print(">>> 2. 数据库落库成功且保留后置 JS 脚本！")

        print("\n=== 3. 模拟前端 openEditApiDialog 映射 ===")
        # 模拟前端修复后的映射逻辑
        apiPostActionsList = [
            {
                "enabled": a.get("enabled", True),
                "name": a.get("name", ""),
                "type": a.get("type", "assert_status_code"),
                "expression": a.get("expression", ""),
                "operator": a.get("operator", "equals"),
                "target_value": a.get("target_value", ""),
                "value": a.get("value") if a.get("value") is not None else a.get("script", ""),
                "description": a.get("description", "")
            }
            for a in probe.post_actions
        ]
        print("Frontend mapped post actions:", apiPostActionsList)
        assert len(apiPostActionsList) == 1
        assert apiPostActionsList[0]["value"] != "", "Frontend mapped value should NOT be empty!"
        assert 'pm.environment.set("token"' in apiPostActionsList[0]["value"]
        print(">>> 3. 前端映射测试通过：item.value 完整保留并包含后置 JS 脚本！")

        print("\n=== 4. 模拟前端发送在线调试 (/api/apis/test-run) ===")
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
            post_actions=apiPostActionsList, # 传递前端包含 value 的完整对象
            expected_schema=probe.expected_schema
        )

        with patch("app.services.probe_service.check_http_detailed") as mock_check:
            async def fake_login_resp(url, method, headers, params, body, body_type):
                print(f"Captured Target URL: {url}")
                print(f"Captured Target Body: {body}")
                assert "password" in body and "email" in body
                # 模拟登录接口成功返回带 accessToken 的响应
                fake_json = {
                    "code": 0,
                    "msg": "success",
                    "data": {
                        "accessToken": "ey_login_success_token_778899",
                        "expiresIn": 7200
                    }
                }
                return True, 200, 35, fake_json, None, {}, json.dumps(fake_json)

            mock_check.side_effect = fake_login_resp
            resp = await test_run_api(req_data, db)
            print("Test run response environment updated_variables:", resp["environment"].get("updated_variables"))
            
            # 断言后置脚本成功提取并将 token 写入环境！
            assert resp["environment"]["updated_variables"].get("token") == "ey_login_success_token_778899"
            
            # 断言数据库中的 Environment 也已持久化此 token！
            grp = db.get(ServiceGroup, machine.group_id)
            env = db.get(Environment, grp.environment_id)
            db.refresh(env)
            print("DB environment variables:", env.variables)
            assert env.variables.get("token") == "ey_login_success_token_778899"
            print(">>> 4. 在线调试完全通过：后置 JS 脚本成功执行并将 token 自动同步写入环境持久化！")

if __name__ == "__main__":
    asyncio.run(test_all())
