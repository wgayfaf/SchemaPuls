import os
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\wgayf\.gemini\antigravity-ide\brain\d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f"

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
}"""

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        print("1. Goto homepage", flush=True)
        page.goto("http://127.0.0.1:3000", wait_until="commit", timeout=15000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2500)
        
        # 切换到机器管理
        print("2. Click 机器管理", flush=True)
        page.locator(".el-menu-item:has-text('机器管理')").first.click()
        page.wait_for_timeout(1000)
        
        # 打开导入弹窗
        print("3. Open import dialog", flush=True)
        page.locator("button:has-text('导入')").first.click()
        page.wait_for_timeout(1500)
        
        # 切换到粘贴文本标签页
        print("4. Switch to paste tab", flush=True)
        page.locator(".el-tabs__item:has-text('粘贴')").first.click()
        page.wait_for_timeout(800)
        
        # 填入 user_login_json
        page.locator(".el-dialog textarea").first.fill(user_login_json)
        page.wait_for_timeout(800)
        
        # 点击开始解析
        print("5. Parse preview", flush=True)
        page.locator("button:has-text('开始解析')").first.click()
        page.wait_for_timeout(3000)
        
        # 截图 1: 导入预览弹窗（同时展示前置脚本和测试断言标签）
        shot1 = os.path.join(ARTIFACT_DIR, "postman_login_import_preview.png")
        page.screenshot(path=shot1)
        print("Shot 1 saved:", shot1, flush=True)
        
        # 点击确认导入
        print("6. Confirm import", flush=True)
        page.locator("button:has-text('确认导入')").first.click()
        page.wait_for_timeout(2500)
        
        # 点击查看导入的接口
        print("7. View imported apis", flush=True)
        page.locator("button:has-text('查看导入的接口')").first.click()
        page.wait_for_timeout(2000)
        
        # 打开刚导入的“邮箱登录”接口编辑弹窗
        print("8. Open edit dialog for 邮箱登录", flush=True)
        page.locator("tr:has-text('邮箱登录') button:has-text('编辑')").first.click()
        page.wait_for_timeout(2000)
        
        # 切换到【后置操作】标签页
        print("9. Switch to 后置操作 tab", flush=True)
        page.locator(".el-dialog .el-tabs__item:has-text('后置操作')").first.click()
        page.wait_for_timeout(1200)
        
        # 截图 2: 后置操作标签页中完整呈现的 JavaScript 脚本与代码高亮框
        shot2 = os.path.join(ARTIFACT_DIR, "postman_login_post_actions_js.png")
        page.screenshot(path=shot2)
        print("Shot 2 saved:", shot2, flush=True)
        
        # 点击发送调试
        print("10. Send test run", flush=True)
        page.locator(".pm-send-btn").first.click()
        page.wait_for_timeout(3500)
        
        # 截图 3: 调试响应面板
        shot3 = os.path.join(ARTIFACT_DIR, "postman_login_debug_response.png")
        page.screenshot(path=shot3)
        print("Shot 3 saved:", shot3, flush=True)
        
        browser.close()
        print("All shots captured successfully!", flush=True)

if __name__ == "__main__":
    main()
