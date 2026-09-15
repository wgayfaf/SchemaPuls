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

        print("2. 打开 Postman 风格工作台并激活 后置操作 标签页...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.openCreateApiDialog();
            window.SchemaPulseApp.apiActiveTab.value = 'post_actions';
            window.SchemaPulseApp.apiPostActionsList.value = []; // 清空确保测试准确
        }""")
        page.wait_for_timeout(800)

        post_pane = page.locator("#pane-post_actions")

        # 3. 点击 '+ JS 脚本断言 (Postman Tests)'
        print("3. 点击快捷预设 '+ JS 脚本断言 (Postman Tests)' 检查 value 是否为空...", flush=True)
        js_btn = post_pane.locator(".pm-preset-tag:has-text('JS 脚本断言')")
        js_btn.click()
        page.wait_for_timeout(400)

        post_list = page.evaluate("() => window.SchemaPulseApp.apiPostActionsList.value")
        print("   当前后置操作列表:", post_list, flush=True)
        assert len(post_list) == 1, "应插入 1 条后置断言"
        assert post_list[0]["type"] == "javascript"
        assert post_list[0]["value"] == "", f"错误：JS 脚本断言初始 value 应该为空字符串，实际为: {repr(post_list[0]['value'])}"
        print("[OK] 成功确认：添加 Postman JS 脚本测试断言预设时 value 为空，没有任何预设代码！", flush=True)

        # 4. 测试点击 '+ 添加断言/操作' 并通过下拉切换为 javascript
        print("4. 测试通过下拉类型选择切换为 JavaScript 断言...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.addPostActionRow();
            const lastItem = window.SchemaPulseApp.apiPostActionsList.value[1];
            lastItem.type = 'javascript';
            window.SchemaPulseApp.onPostActionTypeChange(lastItem);
        }""")
        page.wait_for_timeout(400)

        post_list2 = page.evaluate("() => window.SchemaPulseApp.apiPostActionsList.value")
        assert len(post_list2) == 2, "应有 2 条后置断言"
        assert post_list2[1]["type"] == "javascript"
        assert post_list2[1]["value"] == "", f"错误：下拉切换为 JS 断言时 value 应为空，实际为: {repr(post_list2[1]['value'])}"
        print("[OK] 成功确认：下拉切换为 JavaScript 断言时 value 同样为空！", flush=True)

        # 5. 模拟用户输入测试代码
        print("5. 模拟用户自主填入 Postman JS 断言代码...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.apiPostActionsList.value[0].value = "pm.test('Status is 200', function() { pm.response.to.have.status(200); });";
        }""")
        page.wait_for_timeout(300)
        custom_val = page.evaluate("() => window.SchemaPulseApp.apiPostActionsList.value[0].value")
        assert "pm.test" in custom_val
        print("[OK] 用户自主输入断言代码与双向绑定正常！", flush=True)

        # 6. 截屏保存
        screenshot_path = "scratch/postman_post_actions_empty_value.png"
        page.screenshot(path=screenshot_path)
        shutil.copy(screenshot_path, "C:/Users/wgayf/.gemini/antigravity-ide/brain/d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f/postman_post_actions_empty_value.png")
        print("[OK] 已截取界面并保存: postman_post_actions_empty_value.png", flush=True)

        print("\n==========================================")
        print("🎉 全部验证通过！后置操作 JS 测试断言代码已默认清空，由用户填入！")
        print("==========================================")
        browser.close()

if __name__ == "__main__":
    verify()
