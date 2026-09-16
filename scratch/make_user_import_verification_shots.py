import os
import json
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\wgayf\.gemini\antigravity-ide\brain\d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f"

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

def main():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            
            print("Navigating to http://127.0.0.1:3000 ...", flush=True)
            page.goto("http://127.0.0.1:3000", wait_until="commit", timeout=15000)
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2500)
            
            # 1. 切换至“机器管理”
            print("1. Click 机器管理", flush=True)
            page.locator(".el-menu-item:has-text('机器管理')").first.click()
            page.wait_for_timeout(1000)
            
            # 2. 点击顶部“导入 Postman 集合”或列表操作栏中的导入
            print("2. Open Postman import dialog", flush=True)
            import_btn = page.locator("button:has-text('导入 Postman')").first
            if not import_btn.is_visible():
                import_btn = page.locator("button:has-text('导入')").first
            import_btn.click()
            page.wait_for_timeout(1500)
            
            # 3. 切换至“粘贴 JSON 文本”标签页
            print("3. Switch to paste JSON tab", flush=True)
            page.locator(".el-tabs__item:has-text('粘贴')").first.click()
            page.wait_for_timeout(800)
            
            # 填入 user_json
            print("Filling user JSON into textarea...", flush=True)
            textarea = page.locator(".el-dialog textarea").first
            textarea.fill(user_json)
            page.wait_for_timeout(800)
            
            # 点击开始解析
            print("4. Click parse preview", flush=True)
            page.locator("button:has-text('开始解析')").first.click()
            page.wait_for_timeout(3000)
            
            # 截图 1: 导入预览对话框
            shot1 = os.path.join(ARTIFACT_DIR, "postman_path_auth_preview.png")
            page.screenshot(path=shot1)
            print("Shot 1 saved:", shot1, flush=True)
            
            # 5. 点击“确认导入已选 (1) 个接口”
            print("5. Confirm import", flush=True)
            confirm_btn = page.locator("button:has-text('确认导入')").first
            confirm_btn.click()
            page.wait_for_timeout(2500)
            
            # 6. 点击“查看导入的接口”
            print("6. Go to imported apis view", flush=True)
            view_imported_btn = page.locator("button:has-text('查看导入的接口')").first
            view_imported_btn.click()
            page.wait_for_timeout(2000)
            
            # 7. 在接口列表中找到刚刚导入的“table / 表格 / 获取表格详情”，点击“编辑 / 调试”
            print("7. Open API workbench dialog", flush=True)
            edit_btn = page.locator("tr:has-text('获取表格详情') button:has-text('编辑')").first
            edit_btn.click()
            page.wait_for_timeout(2000)
            
            # 截图 2: 工作台 Params 标签页与路径
            shot2 = os.path.join(ARTIFACT_DIR, "postman_imported_params.png")
            page.screenshot(path=shot2)
            print("Shot 2 saved:", shot2, flush=True)
            
            # 8. 切换至“Auth”标签页
            print("8. Switch to Auth tab", flush=True)
            page.locator(".el-dialog .el-tabs__item:has-text('Auth')").first.click()
            page.wait_for_timeout(1000)
            
            # 截图 3: 工作台 Auth 标签页
            shot3 = os.path.join(ARTIFACT_DIR, "postman_imported_auth.png")
            page.screenshot(path=shot3)
            print("Shot 3 saved:", shot3, flush=True)
            
            # 9. 点击“发送调试”按钮
            print("9. Click send test run", flush=True)
            send_btn = page.locator(".pm-send-btn").first
            send_btn.click()
            page.wait_for_timeout(3500)
            
            # 截图 4: 调试完成后的响应与发包信息
            shot4 = os.path.join(ARTIFACT_DIR, "postman_imported_test_run.png")
            page.screenshot(path=shot4)
            print("Shot 4 saved:", shot4, flush=True)
            
            browser.close()
            print("All verification shots captured successfully!", flush=True)
    except Exception as e:
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
