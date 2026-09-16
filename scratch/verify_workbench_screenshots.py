import asyncio
from playwright.async_api import async_playwright
import shutil, os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.goto("http://127.0.0.1:3000/")
        await page.wait_for_timeout(2000)

        # 直接通过 window.app 打开第一条接口的 Postman 工作台进行编辑
        await page.evaluate("""() => {
            window.app.switchNav('api_management');
            if (window.app.apiList && window.app.apiList.length > 0) {
                window.app.openEditApiDialog(window.app.apiList[0]);
            }
        }""")
        await page.wait_for_timeout(1500)

        # 切换到 Body Tab
        body_tab = page.locator(".el-tabs__item:has-text('Body')").first
        if await body_tab.count() > 0:
            await body_tab.click()
            await page.wait_for_timeout(500)

        # 点击【发送】按钮进行调试发包
        send_btn = page.locator(".pm-send-btn").first
        if await send_btn.count() > 0:
            await send_btn.click()
            await page.wait_for_timeout(3500)

        # 截图保存调试完成的工作台
        await page.screenshot(path="workbench_fixed_debug_success.png")
        print("Saved workbench_fixed_debug_success.png")

        # 点击右上角环境变量徽章查看弹窗
        badge = page.locator(".pm-env-badge").first
        if await badge.count() > 0:
            await badge.click()
            await page.wait_for_timeout(1000)
            await page.screenshot(path="workbench_env_dialog_verified.png")
            print("Saved workbench_env_dialog_verified.png")

        await browser.close()

    artifact_dir = r"C:\Users\wgayf\.gemini\antigravity-ide\brain\d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f"
    for fname in ["workbench_fixed_debug_success.png", "workbench_env_dialog_verified.png"]:
        if os.path.exists(fname):
            shutil.copy(fname, os.path.join(artifact_dir, fname))
            print("Copied to artifact:", fname)

if __name__ == "__main__":
    asyncio.run(main())
