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
        page.goto("http://127.0.0.1:3000", timeout=20000)
        page.wait_for_selector("#app", timeout=15000)
        page.wait_for_timeout(1000)

        # 检查 Vue 是否就绪
        page.wait_for_function("() => !!window.SchemaPulseApp", timeout=15000)
        is_mounted = page.evaluate("() => !!window.SchemaPulseApp")
        assert is_mounted, "Vue 实例未就绪！"

        print("2. 打开 Postman 风格工作台并激活 Auth 标签页...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.openCreateApiDialog();
            window.SchemaPulseApp.apiActiveTab.value = 'auth';
            window.SchemaPulseApp.apiAuthType.value = 'bearer';
        }""")
        page.wait_for_timeout(800)

        auth_pane = page.locator("#pane-auth")
        auth_html = auth_pane.inner_html()

        print("3. 校验 Auth 标签页中已不再包含 '动态预请求宏引擎已就绪' 卡片...", flush=True)
        assert "动态预请求宏引擎已就绪" not in auth_html, "错误：Auth 标签页仍包含 '动态预请求宏引擎已就绪'！"
        assert "pm-macro-card" not in auth_html, "错误：Auth 标签页仍包含 'pm-macro-card'！"
        print("[OK] 成功确认：'动态预请求宏引擎已就绪' 卡片已彻底移除！", flush=True)

        # 4. 验证认证类型切换正常
        # 切换到 basic
        page.evaluate("() => { window.SchemaPulseApp.apiAuthType.value = 'basic'; }")
        page.wait_for_timeout(300)
        basic_html = page.locator("#pane-auth").inner_html()
        assert "用户名" in basic_html and "密码" in basic_html, "Basic Auth 输入框渲染失败！"

        # 切换到 custom_header
        page.evaluate("() => { window.SchemaPulseApp.apiAuthType.value = 'custom_header'; }")
        page.wait_for_timeout(300)
        custom_html = page.locator("#pane-auth").inner_html()
        assert "自定义 Header" in custom_html, "Custom Header 输入框渲染失败！"

        # 5. 截图存档 (Bearer Token 状态)
        page.evaluate("() => { window.SchemaPulseApp.apiAuthType.value = 'bearer'; }")
        page.wait_for_timeout(300)
        screenshot_path = "scratch/postman_auth_clean.png"
        page.screenshot(path=screenshot_path)
        shutil.copy(screenshot_path, "C:/Users/wgayf/.gemini/antigravity-ide/brain/d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f/postman_auth_clean.png")
        print("[OK] 已截取 Auth 标签页精简后界面并保存: postman_auth_clean.png", flush=True)

        print("\n==========================================")
        print("🎉 验证全部通过！Auth 下的 '动态预请求宏引擎已就绪' 卡片已成功移除！")
        print("==========================================")
        browser.close()

if __name__ == "__main__":
    verify()
