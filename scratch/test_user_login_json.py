import json, sys
sys.path.insert(0, 'backend')
from app.services.postman_importer import parse_postman_package

raw_json = '''{
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
                                            "const jsrsasign = require('jsrsasign');"
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
                                            "",
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
}'''

res = parse_postman_package(raw_json.encode('utf-8'), "login.json")
print("Parsed APIs count:", len(res["apis"]))
for api in res["apis"]:
    print("API Name:", api["name"])
    print("Pre actions count:", len(api["pre_actions"]))
    print("Post actions count:", len(api["post_actions"]))
    print("Post actions:", json.dumps(api["post_actions"], indent=2, ensure_ascii=False))
