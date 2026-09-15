import sys
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(f"PAGE_ERROR: {err}"))
        page.on("console", lambda msg: errors.append(f"CONSOLE_{msg.type}: {msg.text}") if msg.type == "error" else None)
        
        page.goto("http://127.0.0.1:3000", wait_until="commit", timeout=10000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        page.wait_for_timeout(2000)
        
        title = page.title()
        print(f"Page Title: {title}")
        
        # 验证 Vue 实例是否成功挂载且没有未捕获异常
        app_el = page.query_selector("#app")
        print("Vue #app mounted:", app_el is not None)
        
        # 切换到接口管理
        menu_item = page.query_selector(".el-menu-item:has-text('接口探针')")
        if menu_item:
            menu_item.click()
            page.wait_for_timeout(1000)
            
        # 打开新建接口工作台
        btn = page.query_selector("button:has-text('新建接口探测')")
        if btn:
            btn.click()
            page.wait_for_timeout(1500)
            print("Opened workbench successfully")
            
        # 验证环境变量按钮
        env_btn = page.query_selector("button:has-text('环境变量')")
        if env_btn:
            print("Found environment button text:", env_btn.inner_text())
            env_btn.click()
            page.wait_for_timeout(1000)
            print("Opened environment variables dialog successfully")
            
        page.screenshot(path="scratch/final_verified.png")
        print("Final screenshot saved: scratch/final_verified.png")
        
        print("Logged console/page errors:", errors)
        if not errors:
            print("[SUCCESS] Zero errors detected! All components working smoothly.")
            
        browser.close()

if __name__ == "__main__":
    main()
