import json, re, sys
sys.path.insert(0, 'backend')
from typing import Dict, Any, List, Optional, Tuple

data_str = '''{
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
}'''

def _parse_postman_auth(auth_obj: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    if not auth_obj or not isinstance(auth_obj, dict):
        return "none", {}
    auth_type_raw = auth_obj.get("type", "").lower()
    if not auth_type_raw or auth_type_raw == "noauth":
        return "none", {}
    if auth_type_raw == "bearer":
        bearer_list = auth_obj.get("bearer", [])
        token_val = ""
        if isinstance(bearer_list, list):
            for item in bearer_list:
                if isinstance(item, dict) and item.get("key") == "token":
                    token_val = str(item.get("value", ""))
        elif isinstance(bearer_list, dict):
            token_val = str(bearer_list.get("token", ""))
        return "bearer", {"token": token_val}
    elif auth_type_raw == "basic":
        basic_list = auth_obj.get("basic", [])
        u, p = "", ""
        if isinstance(basic_list, list):
            for item in basic_list:
                if isinstance(item, dict):
                    if item.get("key") == "username":
                        u = str(item.get("value", ""))
                    elif item.get("key") == "password":
                        p = str(item.get("value", ""))
        elif isinstance(basic_list, dict):
            u = str(basic_list.get("username", ""))
            p = str(basic_list.get("password", ""))
        return "basic", {"username": u, "password": p}
    elif auth_type_raw == "apikey":
        apikey_list = auth_obj.get("apikey", [])
        in_loc, key_name, val = "", "", ""
        if isinstance(apikey_list, list):
            for item in apikey_list:
                if isinstance(item, dict):
                    k = item.get("key")
                    v = str(item.get("value", ""))
                    if k == "in":
                        in_loc = v.lower()
                    elif k == "key":
                        key_name = v
                    elif k == "value":
                        val = v
        elif isinstance(apikey_list, dict):
            in_loc = str(apikey_list.get("in", "")).lower()
            key_name = str(apikey_list.get("key", ""))
            val = str(apikey_list.get("value", ""))
        if key_name.lower() == "authorization" and val.lower().startswith("bearer "):
            return "bearer", {"token": val[7:].strip()}
        elif key_name:
            return "custom_header", {"header_key": key_name, "header_value": val}
    return "none", {}

auth_type, auth_cfg = _parse_postman_auth(json.loads(data_str)["item"][0]["item"][0]["item"][0]["request"]["auth"])
print("Parsed Auth:")
print("  type:", auth_type)
print("  config:", auth_cfg)

assert auth_type == "custom_header"
assert auth_cfg == {"header_key": "Authorization", "header_value": "{{token}}"}
print("Auth parsed successfully!")
