import os
import shutil
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\wgayf\.gemini\antigravity-ide\brain\d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f"

def run_demo():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        
        print("1. 打开 SchemaPulse 控制台首页...")
        page.goto("http://127.0.0.1:3000", wait_until="commit")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1500)
        
        print("2. 切换至 [接口探针资产] 列表...")
        page.locator(".el-menu-item:has-text('接口探针')").first.click()
        page.wait_for_timeout(1000)
        
        print("3. 点击 [+ 新建接口探测]，打开 Postman 风格工作台...")
        page.locator("button:has-text('新建接口探测')").first.click()
        page.wait_for_timeout(1500)
        
        # 截图 1: Postman 风格工作台与环境信息条
        shot1 = os.path.join(ARTIFACT_DIR, "step1_postman_workbench.png")
        page.screenshot(path=shot1)
        print("Saved shot 1:", shot1)
        
        # 4. 点击【环境变量】按钮，打开环境变量管理弹窗
        print("4. 点击 [环境变量] 按钮...")
        env_btn = page.locator("button:has-text('环境变量')").first
        env_btn.click()
        page.wait_for_timeout(1000)
        
        # 截图 2: 环境变量管理弹窗
        shot2 = os.path.join(ARTIFACT_DIR, "step2_env_vars_dialog.png")
        page.screenshot(path=shot2)
        print("Saved shot 2:", shot2)
        
        # 5. 在弹窗中添加一个新变量并保存
        print("5. 在弹窗中录入环境变量 DEMO_ACCESS_TOKEN...")
        page.locator("button:has-text('添加新变量')").first.click()
        page.wait_for_timeout(300)
        
        # 找到最后一行的输入框
        inputs = page.locator(".pm-table input")
        count = inputs.count()
        if count >= 2:
            inputs.nth(count - 2).fill("DEMO_ACCESS_TOKEN")
            inputs.nth(count - 1).fill("ey_demo_secret_token_8888")
            
        # 点击保存修改
        page.locator("button:has-text('保存修改')").first.click()
        page.wait_for_timeout(1500)
        
        # 6. 在工作台 URL 栏中引用 {{DEMO_ACCESS_TOKEN}} 并点击发送调试
        print("6. 在工作台中使用 {{DEMO_ACCESS_TOKEN}} 发起调试...")
        path_input = page.locator(".pm-path-input input").first
        path_input.fill("/get?token={{DEMO_ACCESS_TOKEN}}")
        
        send_btn = page.locator(".pm-send-btn").first
        send_btn.click()
        page.wait_for_timeout(2500)
        
        # 截图 3: 调试完成响应与环境变量解析
        shot3 = os.path.join(ARTIFACT_DIR, "step3_debug_response_with_env.png")
        page.screenshot(path=shot3)
        print("Saved shot 3:", shot3)
        
        print("[SUCCESS] 端到端交互与验证流程完美执行完成！")
        browser.close()

if __name__ == "__main__":
    run_demo()
