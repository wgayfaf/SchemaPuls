import time
from playwright.sync_api import sync_playwright

def main():
    print("=== Starting Playwright UI Verification for Environment Variables Sync ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. 访问系统前端
        page.goto("http://127.0.0.1:3000")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # 2. 点击进入【环境管理】
        print("1. Navigating to Environment Management...")
        env_menu = page.locator(".el-menu-item").filter(has_text="环境管理")
        env_menu.click()
        time.sleep(1)

        # 验证环境管理表格中的“环境变量池”列及“变量管理”按钮
        env_table = page.locator(".wb-card").filter(has_text="运行环境列表")
        assert env_table.is_visible(), "Environment table not visible"
        
        # 截图记录环境管理页面中的环境变量列
        env_list_screenshot = "env_list_with_vars.png"
        page.screenshot(path=env_list_screenshot)
        print(f"Saved screenshot: {env_list_screenshot}")

        # 点击第一行的【变量管理】按钮
        print("2. Clicking '变量管理' in environment row...")
        var_manage_btn = page.locator("button:has-text('变量管理')").first
        var_manage_btn.click()
        time.sleep(1)

        # 验证弹出的环境变量管理对话框
        dialog = page.locator(".el-dialog").filter(has_text="环境变量管理")
        assert dialog.is_visible(), "Environment variables dialog not visible!"
        
        # 检查是否包含刚才生成的变量
        dialog_text = dialog.inner_text()
        assert "SYNC_PRE_FORM" in dialog_text, "SYNC_PRE_FORM not found in dialog!"
        assert "SYNC_PRE_JS" in dialog_text, "SYNC_PRE_JS not found in dialog!"
        assert "SYNC_POST_JS" in dialog_text, "SYNC_POST_JS not found in dialog!"
        print("--> Variables verified in Environment Management dialog!")

        env_dialog_screenshot = "env_management_vars_dialog.png"
        page.screenshot(path=env_dialog_screenshot)
        print(f"Saved screenshot: {env_dialog_screenshot}")

        # 关闭弹窗
        page.locator(".el-dialog button:has-text('取消')").click()
        time.sleep(0.5)

        # 3. 点击进入【接口管理】
        print("3. Navigating to API Management...")
        api_menu = page.locator(".el-menu-item").filter(has_text="接口管理")
        api_menu.click()
        time.sleep(1)

        # 点击【新建接口】
        print("4. Opening API Workbench...")
        page.locator("button:has-text('新建接口')").first.click()
        time.sleep(1)

        workbench = page.locator(".el-dialog").filter(has_text="新建接口探测")
        assert workbench.is_visible(), "API Workbench dialog not visible!"

        # 点击工作台顶部的【环境变量 (N)】按钮
        print("5. Clicking top environment variables button in workbench...")
        top_env_btn = workbench.locator("button:has-text('环境变量')")
        top_env_btn.click()
        time.sleep(1)

        # 验证弹出的环境变量弹窗，且包含最新变量
        var_dialog_wb = page.locator(".el-dialog").filter(has_text="环境变量管理")
        assert var_dialog_wb.is_visible(), "Env vars dialog in workbench not visible!"
        assert "SYNC_PRE_FORM" in var_dialog_wb.inner_text()
        print("--> Environment variables verified inside Workbench!")

        wb_env_screenshot = "workbench_env_vars_dialog.png"
        page.screenshot(path=wb_env_screenshot)
        print(f"Saved screenshot: {wb_env_screenshot}")

        # 关闭变量弹窗
        page.locator(".el-dialog").filter(has_text="环境变量管理").locator("button:has-text('取消')").click()
        time.sleep(1)

        # 4. 在工作台中添加前置操作【设置变量】，并点击【发送】
        print("6. Adding pre-action set_variable in workbench via evaluate...")
        page.evaluate("""() => {
            window.SchemaPulseApp.apiPreActionsList.value.push({
                enabled: true,
                type: 'set_variable',
                key: 'UI_DYNAMIC_TOKEN',
                value: 'dynamic_secret_888',
                description: '前置操作注入测试变量'
            });
            window.SchemaPulseApp.apiForm.value.http_path = '/api/test_dynamic_sync';
        }""")
        time.sleep(0.5)

        # 点击【发送】
        print("7. Clicking '.pm-send-btn' (发送)...")
        page.locator(".pm-send-btn").first.click()
        
        # 等待调试完成提示
        page.wait_for_selector("text=已自动将", timeout=8000)
        time.sleep(1)

        debug_screenshot = "workbench_debug_sync_success.png"
        page.screenshot(path=debug_screenshot)
        print(f"Saved screenshot: {debug_screenshot}")

        # 5. 再次点击顶部的【环境变量】按钮，验证刚刚前置操作设置的 UI_DYNAMIC_TOKEN 已经即时同步更新在弹窗中！
        print("8. Re-opening environment variables dialog to verify immediate sync...")
        workbench.locator("button:has-text('环境变量')").click()
        time.sleep(1)

        dialog_final = page.locator(".el-dialog").filter(has_text="环境变量管理")
        assert dialog_final.is_visible()
        final_text = dialog_final.inner_text()
        assert "UI_DYNAMIC_TOKEN" in final_text, "UI_DYNAMIC_TOKEN not found in final dialog!"
        print("--> UI_DYNAMIC_TOKEN successfully verified in dynamically re-opened dialog!")

        final_sync_screenshot = "env_vars_dialog_after_dynamic_sync.png"
        page.screenshot(path=final_sync_screenshot)
        print(f"Saved screenshot: {final_sync_screenshot}")

        print("\n=== ALL PLAYWRIGHT UI VERIFICATIONS PASSED 100%! ===")
        browser.close()

if __name__ == "__main__":
    main()
