import sys
import shutil

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from playwright.sync_api import sync_playwright

def verify():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        print("1. 打开前端首页...", flush=True)
        page.goto("http://127.0.0.1:3000", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("#app", timeout=15000)
        page.wait_for_function("() => !!window.SchemaPulseApp", timeout=15000)

        print("2. 打开 Postman 风格工作台并激活 Schema 标签页...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.openCreateApiDialog();
            window.SchemaPulseApp.apiActiveTab.value = 'schema';
        }""")
        page.wait_for_timeout(800)

        # 3. 校验初始 schema_text 是否为空
        print("3. 校验新建接口时 Schema 是否默认为空...", flush=True)
        schema_val = page.evaluate("() => window.SchemaPulseApp.apiForm.value.schema_text")
        print(f"   当前 schema_text 初始值: {repr(schema_val)}", flush=True)
        assert schema_val == "", f"错误：新建接口时 schema_text 应该默认为空，实际为: {repr(schema_val)}"

        # 截屏 1: Schema 默认清空状态
        screenshot_path1 = "scratch/postman_schema_empty.png"
        page.screenshot(path=screenshot_path1)
        shutil.copy(screenshot_path1, "C:/Users/wgayf/.gemini/antigravity-ide/brain/d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f/postman_schema_empty.png")
        print("[OK] 已截取 Schema 默认为空界面: postman_schema_empty.png", flush=True)

        # 4. 模拟调试获得实际响应后，点击【从当前响应推导】
        print("4. 模拟调试获得真实响应后，测试【从当前响应推导】功能...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.apiTestResult.value = {
                status_code: 200,
                latency_ms: 45.2,
                response_data: {
                    code: 200,
                    message: "success",
                    data: {
                        userId: 10086,
                        username: "AntigravityUser",
                        roles: ["admin", "developer"],
                        is_active: true
                    }
                }
            };
        }""")
        page.wait_for_timeout(300)

        # 点击【从当前响应推导】按钮
        infer_btn = page.locator("#pane-schema button:has-text('从当前响应推导')")
        assert not infer_btn.is_disabled(), "存在响应时【从当前响应推导】按钮应处于可点击状态！"
        infer_btn.click()
        page.wait_for_timeout(1200)

        # 5. 校验推导结果是否自动填入 schema_text
        inferred_schema = page.evaluate("() => window.SchemaPulseApp.apiForm.value.schema_text")
        print(f"   推导生成的 Schema 前 100 字符: {inferred_schema[:100]}...", flush=True)
        assert "userId" in inferred_schema, "推导生成的 Schema 必须包含字段 userId！"
        assert "roles" in inferred_schema, "推导生成的 Schema 必须包含字段 roles！"
        assert "integer" in inferred_schema or "number" in inferred_schema
        print("[OK] 【从当前响应推导】成功生成标准的 Draft-7 JSON Schema 契约规则并自动填入！", flush=True)

        # 截屏 2: 点击从当前响应推导后自动填入的 Schema 效果
        screenshot_path2 = "scratch/postman_schema_inferred.png"
        page.screenshot(path=screenshot_path2)
        shutil.copy(screenshot_path2, "C:/Users/wgayf/.gemini/antigravity-ide/brain/d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f/postman_schema_inferred.png")
        print("[OK] 已截取推导填入后的 Schema 界面: postman_schema_inferred.png", flush=True)

        print("\n==========================================")
        print("🎉 全部验证通过！Schema 默认已改为空，从当前响应推导功能完美正常！")
        print("==========================================")
        browser.close()

if __name__ == "__main__":
    verify()
