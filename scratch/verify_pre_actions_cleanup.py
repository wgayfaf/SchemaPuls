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
        page.wait_for_function("() => !!window.SchemaPulseApp", timeout=15000)

        print("2. 打开 Postman 风格工作台并激活 前置操作 标签页...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.openCreateApiDialog();
            window.SchemaPulseApp.apiActiveTab.value = 'pre_actions';
        }""")
        page.wait_for_timeout(800)

        pre_pane = page.locator("#pane-pre_actions")
        preset_bar_text = pre_pane.locator(".pm-preset-bar").inner_text()
        print("   当前快速预设栏文本:", preset_bar_text.replace('\n', ' '), flush=True)

        print("3. 校验已移除的预设项...", flush=True)
        assert "设置当前时间戳变量" not in preset_bar_text, "错误：仍包含 '设置当前时间戳变量'！"
        assert "注入动态 UUID 跟踪头" not in preset_bar_text, "错误：仍包含 '注入动态 UUID 跟踪头'！"
        assert "注入随机数参数" not in preset_bar_text, "错误：仍包含 '注入随机数参数'！"
        assert "jsrsasign" not in preset_bar_text, "错误：仍包含 'jsrsasign RSA 加密'！"
        assert "crypto-js" not in preset_bar_text, "错误：仍包含 'crypto-js 哈希/签名'！"
        print("[OK] 确认 5 项预设已彻底移除！", flush=True)

        print("4. 校验保留的预设项与操作功能...", flush=True)
        assert "Postman JS 脚本" in preset_bar_text, "错误：丢失 'Postman JS 脚本'！"
        assert "Python 脚本" in preset_bar_text, "错误：丢失 'Python 脚本'！"
        print("[OK] 确认保留 'Postman JS 脚本' 与 'Python 脚本'！", flush=True)

        # 5. 点击 '+ Postman JS 脚本' 验证功能
        js_btn = pre_pane.locator(".pm-preset-tag:has-text('Postman JS 脚本')")
        js_btn.click()
        page.wait_for_timeout(500)
        rows_count = page.evaluate("() => window.SchemaPulseApp.apiPreActionsList.value.length")
        assert rows_count >= 1, "点击预设未能添加前置操作！"
        print(f"[OK] 点击 '+ Postman JS 脚本' 成功插入前置操作，当前条数: {rows_count}", flush=True)

        # 6. 截屏存档
        screenshot_path = "scratch/postman_pre_actions_clean.png"
        page.screenshot(path=screenshot_path)
        shutil.copy(screenshot_path, "C:/Users/wgayf/.gemini/antigravity-ide/brain/d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f/postman_pre_actions_clean.png")
        print("[OK] 已截取 前置操作 选项卡精简后界面并保存: postman_pre_actions_clean.png", flush=True)

        print("\n==========================================")
        print("🎉 验证全部通过！前置操作预设精简成功！")
        print("==========================================")
        browser.close()

if __name__ == "__main__":
    verify()
