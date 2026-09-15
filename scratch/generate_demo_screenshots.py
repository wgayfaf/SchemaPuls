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
        
        # 1. 切换至接口管理菜单
        menu = page.query_selector(".el-menu-item:has-text('接口管理')")
        if menu:
            menu.click()
            page.wait_for_timeout(1000)
            
        # 2. 点击新建接口，打开 Postman 风格工作台
        btn = page.query_selector("button:has-text('新建接口')")
        if btn:
            btn.click()
            page.wait_for_timeout(1500)
            
        shot1 = os.path.join(ARTIFACT_DIR, "step1_postman_workbench.png")
        page.screenshot(path=shot1)
        print("Shot 1 saved:", shot1)
        
        # 3. 点击【环境变量】按钮打开管理弹窗
        env_btn = page.query_selector("button:has-text('环境变量')")
        if env_btn:
            env_btn.click()
            page.wait_for_timeout(1000)
            
        shot2 = os.path.join(ARTIFACT_DIR, "step2_env_vars_dialog.png")
        page.screenshot(path=shot2)
        print("Shot 2 saved:", shot2)
        
        # 4. 关闭弹窗并进行在线调试
        close_btn = page.query_selector(".el-dialog button:has-text('取消')")
        if close_btn:
            close_btn.click()
            page.wait_for_timeout(500)
            
        # 填入带环境变量引用的路径并点击调试
        path_input = page.query_selector(".pm-path-input input")
        if path_input:
            path_input.fill("/get?test={{TEST_VAR}}")
            
        send_btn = page.query_selector(".pm-send-btn")
        if send_btn:
            send_btn.click()
            page.wait_for_timeout(2500)
            
        shot3 = os.path.join(ARTIFACT_DIR, "step3_debug_response_with_env.png")
        page.screenshot(path=shot3)
        print("Shot 3 saved:", shot3)
        
        browser.close()
        print("Done!")

if __name__ == "__main__":
    main()
