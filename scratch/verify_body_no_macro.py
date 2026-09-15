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
        is_mounted = page.evaluate("() => !!window.SchemaPulseApp")
        assert is_mounted, "Vue 实例未就绪！"

        print("2. 打开 Postman 风格工作台并激活 Body 标签页...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.openCreateApiDialog();
            window.SchemaPulseApp.apiActiveTab.value = 'body';
            window.SchemaPulseApp.apiBodyType.value = 'json';
        }""")
        page.wait_for_timeout(800)

        body_pane = page.locator("#pane-body")
        body_html = body_pane.inner_html()

        print("3. 校验 Body 标签页中已不再包含 '插入动态宏'...", flush=True)
        assert "插入动态宏" not in body_html, "错误：Body 标签页仍包含 '插入动态宏'！"
        assert "pm-macro-badge" not in body_html, "错误：Body 标签页仍包含 'pm-macro-badge'！"
        print("[OK] 成功确认：'插入动态宏' 栏目已彻底移除！", flush=True)

        # 4. 验证格式化、压缩、清空等正常功能依然完好
        btn_texts = body_pane.locator("button").all_inner_texts()
        print("   Body 栏按钮:", btn_texts, flush=True)
        assert any("格式化 JSON" in b for b in btn_texts), "格式化按钮丢失！"
        assert any("压缩" in b for b in btn_texts), "压缩按钮丢失！"
        assert any("清空" in b for b in btn_texts), "清空按钮丢失！"

        # 5. 截图存档
        screenshot_path = "scratch/postman_body_no_macro.png"
        page.screenshot(path=screenshot_path)
        shutil.copy(screenshot_path, "C:/Users/wgayf/.gemini/antigravity-ide/brain/d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f/postman_body_no_macro.png")
        print("[OK] 已截取 Body 标签页更新后界面并保存: postman_body_no_macro.png", flush=True)

        print("\n==========================================")
        print("🎉 验证全部通过！Body 下的 '插入动态宏' 已成功移除！")
        print("==========================================")
        browser.close()

if __name__ == "__main__":
    verify()
