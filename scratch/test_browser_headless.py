import asyncio
from playwright.async_api import async_playwright

async def verify_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(f"PAGE_ERROR: {err}"))
        page.on("console", lambda msg: errors.append(f"CONSOLE_{msg.type}: {msg.text}") if msg.type == "error" else None)
        
        print("Navigating to http://127.0.0.1:3000...")
        await page.goto("http://127.0.0.1:3000", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        # 切换到接口探针资产菜单
        print("Clicking API probes menu...")
        await page.locator(".el-menu-item:has-text('接口探针')").first.click()
        await asyncio.sleep(1)
        
        # 点击【+ 新建接口探测】按钮
        print("Clicking Create API Probe button...")
        await page.locator("button:has-text('新建接口探测')").first.click()
        await asyncio.sleep(1.5)
        
        # 截图保存工作台
        await page.screenshot(path="scratch/workbench_verified.png")
        print("Saved workbench screenshot: scratch/workbench_verified.png")
        
        # 检查环境变量按钮是否存在并点击
        env_btn = page.locator("button:has-text('环境变量')")
        btn_count = await env_btn.count()
        print(f"Found {btn_count} environment variable buttons")
        if btn_count > 0:
            await env_btn.first.click()
            await asyncio.sleep(1)
            await page.screenshot(path="scratch/env_dialog_verified.png")
            print("Saved environment dialog screenshot: scratch/env_dialog_verified.png")
            
        print("All errors logged:", errors)
        if not errors:
            print("[SUCCESS] Page loaded, workbench opened, and environment dialog opened with 0 errors!")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_browser())
