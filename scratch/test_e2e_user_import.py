import sys
import os
import json

sys.path.insert(0, os.path.abspath("backend"))

from sqlmodel import Session, select
from app.database import engine
from app.models import MachineNode, ApiProbe, Environment, ServiceGroup
from app.services.postman_importer import parse_postman_package, import_postman_to_machine
from app.services.template_engine import resolve_path_variables, parse_params_to_dict

user_json = """{
    "info": {
        "name": "table",
        "description": "",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [
        {
            "name": "table",
            "description": "",
            "item": [
                {
                    "name": "表格",
                    "description": "",
                    "item": [
                        {
                            "name": "获取表格详情",
                            "description": "",
                            "event": [],
                            "auth": {},
                            "request": {
                                "auth": {
                                    "type": "apikey",
                                    "apikey": [
                                        {
                                            "key": "in",
                                            "value": "header",
                                            "type": "string"
                                        },
                                        {
                                            "key": "key",
                                            "value": "Authorization",
                                            "type": "string"
                                        },
                                        {
                                            "key": "value",
                                            "value": "{{token}}",
                                            "type": "string"
                                        }
                                    ]
                                },
                                "method": "POST",
                                "body": {},
                                "header": [],
                                "url": {
                                    "raw": "{{baseUrl}}/api/table/table-manager/detail/:tableId",
                                    "path": [
                                        "api",
                                        "table",
                                        "table-manager",
                                        "detail",
                                        ":tableId"
                                    ],
                                    "host": [
                                        "{{baseUrl}}"
                                    ],
                                    "query": [],
                                    "variable": [
                                        {
                                            "key": "tableId",
                                            "value": "tbl_Hy",
                                            "description": "",
                                            "type": "string"
                                        }
                                    ]
                                }
                            },
                            "response": []
                        }
                    ],
                    "event": [],
                    "auth": {
                        "type": "apikey",
                        "apikey": [
                            {
                                "key": "in",
                                "value": "header",
                                "type": "string"
                            },
                            {
                                "key": "key",
                                "value": "Authorization",
                                "type": "string"
                            },
                            {
                                "key": "value",
                                "value": "{{token}}",
                                "type": "string"
                            }
                        ]
                    }
                }
            ],
            "event": [],
            "auth": {}
        }
    ],
    "variable": [],
    "event": [],
    "auth": {}
}"""

def test_pipeline():
    print("=== 1. 测试解析 parse_postman_package ===")
    parsed = parse_postman_package(user_json.encode('utf-8'), "collection.json")
    apis = parsed["apis"]
    assert len(apis) == 1, f"Expected 1 api, got {len(apis)}"
    api = apis[0]
    
    print(f"API Name: {api['name']}")
    print(f"HTTP Method: {api['http_method']}")
    print(f"HTTP Path: {api['http_path']}")
    print(f"HTTP Params: {json.dumps(api['http_params'], ensure_ascii=False)}")
    print(f"Auth Type: {api['auth_type']}")
    print(f"Auth Config: {json.dumps(api['auth_config'], ensure_ascii=False)}")
    
    # 验证关键指标
    assert api['http_path'] == "/api/table/table-manager/detail/{tableId}", f"Path format mismatch: {api['http_path']}"
    assert any(p.get('key') == 'tableId' and p.get('value') == 'tbl_Hy' for p in api['http_params']), "Param tableId missing!"
    assert api['auth_type'] == "custom_header", f"Auth type mismatch: {api['auth_type']}"
    assert api['auth_config'].get('header_key') == "Authorization", "Auth header_key mismatch"
    assert api['auth_config'].get('header_value') == "{{token}}", "Auth header_value mismatch"
    print(">>> 1. 解析测试完全通过！")

    print("\n=== 2. 测试路径参数解析与剥离 resolve_path_variables ===")
    raw_params = parse_params_to_dict(api['http_params'])
    resolved_path, remaining_params = resolve_path_variables(api['http_path'], raw_params)
    print(f"Resolved Path: {resolved_path}")
    print(f"Remaining Params: {remaining_params}")
    assert resolved_path == "/api/table/table-manager/detail/tbl_Hy", f"Path resolve failed: {resolved_path}"
    assert "tableId" not in remaining_params, "tableId was not stripped from query params!"
    print(">>> 2. 路径参数插值与剥离完全通过！")

    print("\n=== 3. 测试导入持久化到数据库 import_postman_to_machine ===")
    with Session(engine) as db:
        machine = db.exec(select(MachineNode)).first()
        if not machine:
            print("No machine found in db, skipping db persistence test")
            return
        res = import_postman_to_machine(
            db=db,
            machine_id=machine.id,
            selected_apis=apis,
            conflict_policy="overwrite"
        )
        print(f"Import result: {res}")
        imported_probe = db.get(ApiProbe, res["created_ids"][0]) if res["created_ids"] else None
        if not imported_probe:
            # overwrite 模式下查同名
            imported_probe = db.exec(select(ApiProbe).where(ApiProbe.machine_id == machine.id, ApiProbe.name == api['name'])).first()
        assert imported_probe is not None, "Failed to retrieve imported probe"
        print(f"Database Probe Path: {imported_probe.http_path}")
        print(f"Database Probe Auth Type: {imported_probe.auth_type}")
        print(f"Database Probe Auth Config: {imported_probe.auth_config}")
        print(f"Database Probe Params: {imported_probe.http_params}")
        assert imported_probe.http_path == "/api/table/table-manager/detail/{tableId}"
        assert imported_probe.auth_type == "custom_header"
        assert imported_probe.auth_config == {"header_key": "Authorization", "header_value": "{{token}}"}
        print(">>> 3. 数据库持久化测试完全通过！")

if __name__ == "__main__":
    test_pipeline()
