import asyncio
from playwright.async_api import async_playwright
import shutil, os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.goto("http://127.0.0.1:3000/")
        await page.wait_for_timeout(2000)

        # 打开第一条接口
        await page.evaluate("""() => {
            window.app.switchNav('api_management');
            if (window.app.apiList && window.app.apiList.length > 0) {
                window.app.openEditApiDialog(window.app.apiList[0]);
            }
        }""")
        await page.wait_for_timeout(1500)

        # 发送调试
        send_btn = page.locator(".pm-send-btn").first
        await send_btn.click()
        await page.wait_for_timeout(3500)

        # 点击【发送请求体 (Request Body)】Tab
        req_body_tab = page.locator("button:has-text('发送请求体')").first
        if await req_body_tab.count() > 0:
            await req_body_tab.click()
            await page.wait_for_timeout(500)
            await page.screenshot(path="workbench_rendered_body_verified.png")
            print("Saved workbench_rendered_body_verified.png")

        await browser.close()

    artifact_dir = r"C:\Users\wgayf\.gemini\antigravity-ide\brain\d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f"
    for fname in ["workbench_rendered_body_verified.png"]:
        if os.path.exists(fname):
            shutil.copy(fname, os.path.join(artifact_dir, fname))
            print("Copied to artifact:", fname)

if __name__ == "__main__":
    asyncio.run(main())
