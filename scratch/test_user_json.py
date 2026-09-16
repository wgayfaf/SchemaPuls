import json

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
                            "response": [],
                            "protocolProfileBehavior": {
                                "strictSSL": false,
                                "followRedirects": true
                            }
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

data = json.loads(data_str)
print("Parsed collection successfully!")
