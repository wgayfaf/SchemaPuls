import os
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\wgayf\.gemini\antigravity-ide\brain\d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        page.goto("http://127.0.0.1:3000", wait_until="commit", timeout=10000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)
        
        # 1. 切换至接口管理
        page.locator(".el-menu-item:has-text('接口管理')").first.click()
        page.wait_for_timeout(1000)
        
        # 2. 打开工作台
        page.locator("button:has-text('新建接口')").first.click()
        page.wait_for_timeout(1500)
        
        # 3. 填入使用环境变量的路径
        path_input = page.locator(".pm-path-input input").first
        path_input.fill("/get?token={{POST_TOKEN}}&prefix={{BASE_PREFIX}}")
        page.wait_for_timeout(500)
        
        # 4. 点击发送调试
        send_btn = page.locator(".pm-send-btn").first
        send_btn.click()
        page.wait_for_timeout(3000)
        
        shot3 = os.path.join(ARTIFACT_DIR, "step3_debug_response_with_env.png")
        page.screenshot(path=shot3)
        print("Shot 3 saved:", shot3)
        
        browser.close()
        print("Done!")

if __name__ == "__main__":
    main()
