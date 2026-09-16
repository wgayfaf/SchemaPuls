import os
import sys
import time
from playwright.sync_api import sync_playwright

def main():
    table_zip_path = os.path.abspath("table.zip")
    if not os.path.exists(table_zip_path):
        print(f"Error: {table_zip_path} not found")
        sys.exit(1)

    print("=== Starting Playwright End-to-End Test for Postman Import ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. 访问系统前端页面
        page.goto("http://127.0.0.1:3000")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # 2. 点击进入【机器管理】
        print("1. Navigating to Machine Management...")
        machine_menu = page.locator(".el-menu-item").filter(has_text="机器管理")
        machine_menu.click()
        time.sleep(1)

        # 3. 检查机器列表是否存在机器，点击第一台机器的操作列【导入接口】按钮
        print("2. Opening Postman Import Dialog from Machine list...")
        import_btn = page.locator("button:has-text('导入接口')").first
        if not import_btn.is_visible():
            print("Error: '导入接口' button not found in machine list!")
            sys.exit(1)
        import_btn.click()
        time.sleep(1)

        # 4. 验证弹窗是否显示
        dialog = page.locator(".el-dialog").filter(has_text="从 Postman 导入接口资产")
        if not dialog.is_visible():
            print("Error: Postman import dialog not visible!")
            sys.exit(1)
        print("3. Postman import dialog opened successfully.")

        # 5. 上传 table.zip 文件
        print("4. Uploading table.zip to file input...")
        file_input = page.locator("input[type='file'][accept*='.zip']")
        file_input.set_input_files(table_zip_path)
        
        # 等待解析完成
        print("5. Waiting for Postman parsing result...")
        page.wait_for_selector("text=共解析出", timeout=10000)
        time.sleep(1)

        # 截图保存预览状态
        preview_screenshot = "postman_import_preview.png"
        page.screenshot(path=preview_screenshot)
        print(f"Saved preview screenshot to {preview_screenshot}")

        # 6. 点击确认导入
        confirm_btn = page.locator("button:has-text('确认导入已选')")
        print(f"6. Confirm button text: {confirm_btn.inner_text()}")
        confirm_btn.click()

        # 7. 等待导入成功视图
        page.wait_for_selector("text=Postman 接口导入成功！", timeout=10000)
        time.sleep(1)
        success_screenshot = "postman_import_success.png"
        page.screenshot(path=success_screenshot)
        print(f"Saved success screenshot to {success_screenshot}")

        # 8. 点击前往【接口管理】查看
        print("7. Clicking '前往【接口管理】查看导入的接口'...")
        go_to_api_btn = page.locator("button:has-text('前往【接口管理】查看导入的接口')")
        go_to_api_btn.click()
        time.sleep(1.5)

        # 9. 验证是否已经处于接口管理视图且展示了导入的接口
        api_table = page.locator(".wb-card").filter(has_text="机器接口列表")
        if not api_table.is_visible():
            print("Error: Not in API management view!")
            sys.exit(1)

        apis_screenshot = "postman_imported_apis_view.png"
        page.screenshot(path=apis_screenshot)
        print(f"Saved imported APIs view screenshot to {apis_screenshot}")

        print("=== ALL E2E PLAYWRIGHT TESTS PASSED SUCCESSFULLY! ===")
        browser.close()

if __name__ == "__main__":
    main()
