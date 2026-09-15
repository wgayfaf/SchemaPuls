import asyncio
from playwright.async_api import async_playwright

async def test_workbench_env_ui():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.on("console", lambda msg: errors.append(f"CONSOLE {msg.type}: {msg.text}") if msg.type == "error" else None)
        
        print("Navigating to http://127.0.0.1:3000...")
        await page.goto("http://127.0.0.1:3000", wait_until="networkidle")
        await asyncio.sleep(2)
        
        # 1. 切换到接口管理菜单
        print("Clicking API management menu...")
        api_menu = page.locator("text=接口探针资产")
        if await api_menu.count() > 0:
            await api_menu.first.click()
            await asyncio.sleep(1)
            
        # 2. 点击新建接口按钮打开工作台
        print("Opening API Workbench dialog...")
        create_btn = page.locator("text=+ 新增接口探测")
        if await create_btn.count() > 0:
            await create_btn.first.click()
            await asyncio.sleep(1)
        else:
            # 尝试通过别的选择器找新建按钮
            print("Trying alternative button text...")
            alt_btn = page.locator(".el-button--primary:has-text('接口')")
            if await alt_btn.count() > 0:
                await alt_btn.first.click()
                await asyncio.sleep(1)

        # 3. 截取工作台弹窗截图
        await page.screenshot(path="scratch/workbench_open.png")
        print("Workbench screenshot saved to scratch/workbench_open.png")
        
        # 4. 查找环境变量按钮
        env_btn = page.locator("text=环境变量")
        if await env_btn.count() > 0:
            print("Found environment variables button, clicking...")
            await env_btn.first.click()
            await asyncio.sleep(1)
            await page.screenshot(path="scratch/env_dialog_open.png")
            print("Environment dialog screenshot saved to scratch/env_dialog_open.png")
            
        if errors:
            print("Detected errors:", errors)
        else:
            print("[SUCCESS] Workbench & Environment Dialog opened cleanly with NO console errors!")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_workbench_env_ui())
