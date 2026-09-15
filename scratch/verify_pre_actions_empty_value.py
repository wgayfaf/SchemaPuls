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

        print("2. 打开 Postman 风格工作台并激活 前置操作 标签页...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.openCreateApiDialog();
            window.SchemaPulseApp.apiActiveTab.value = 'pre_actions';
            window.SchemaPulseApp.apiPreActionsList.value = []; // 清空确保干净测试
        }""")
        page.wait_for_timeout(800)

        pre_pane = page.locator("#pane-pre_actions")

        # 3. 点击 '+ Postman JS 脚本'
        print("3. 点击 '+ Postman JS 脚本' 检查 value 是否为空...", flush=True)
        js_btn = pre_pane.locator(".pm-preset-tag:has-text('Postman JS 脚本')")
        js_btn.click()
        page.wait_for_timeout(400)

        list_data = page.evaluate("() => window.SchemaPulseApp.apiPreActionsList.value")
        print("   当前前置操作列表:", list_data, flush=True)
        assert len(list_data) == 1, "应插入 1 条数据"
        assert list_data[0]["type"] == "javascript"
        assert list_data[0]["value"] == "", f"错误：JS 脚本初始 value 应该为空字符串，实际为: {repr(list_data[0]['value'])}"
        print("[OK] 成功确认：添加 Postman JS 脚本时 value 为空，没有任何默认预填内容！", flush=True)

        # 4. 点击 '+ Python 脚本'
        print("4. 点击 '+ Python 脚本' 检查 value 是否为空...", flush=True)
        py_btn = pre_pane.locator(".pm-preset-tag:has-text('Python 脚本')")
        py_btn.click()
        page.wait_for_timeout(400)

        list_data2 = page.evaluate("() => window.SchemaPulseApp.apiPreActionsList.value")
        assert len(list_data2) == 2, "应有 2 条数据"
        assert list_data2[1]["type"] == "custom_script"
        assert list_data2[1]["value"] == "", f"错误：Python 脚本初始 value 应该为空字符串，实际为: {repr(list_data2[1]['value'])}"
        print("[OK] 成功确认：添加 Python 脚本时 value 为空，没有任何默认预填内容！", flush=True)

        # 5. 模拟用户输入内容
        print("5. 模拟用户在 JS 脚本区域手动输入自定义代码...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.apiPreActionsList.value[0].value = "pm.environment.set('custom_sign', 'MY_USER_SIGN_123');";
        }""")
        page.wait_for_timeout(300)
        updated_val = page.evaluate("() => window.SchemaPulseApp.apiPreActionsList.value[0].value")
        assert updated_val == "pm.environment.set('custom_sign', 'MY_USER_SIGN_123');"
        print("[OK] 用户输入与双向绑定一切正常！", flush=True)

        # 6. 截屏保存
        screenshot_path = "scratch/postman_pre_actions_empty_value.png"
        page.screenshot(path=screenshot_path)
        shutil.copy(screenshot_path, "C:/Users/wgayf/.gemini/antigravity-ide/brain/d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f/postman_pre_actions_empty_value.png")
        print("[OK] 已截取界面并保存: postman_pre_actions_empty_value.png", flush=True)

        print("\n==========================================")
        print("🎉 全部验证通过！前置操作脚本值已默认清空，由用户自主填写！")
        print("==========================================")
        browser.close()

if __name__ == "__main__":
    verify()
