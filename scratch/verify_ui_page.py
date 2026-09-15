import asyncio
from playwright.async_api import async_playwright

async def verify_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.on("console", lambda msg: errors.append(f"CONSOLE {msg.type}: {msg.text}") if msg.type == "error" else None)
        
        print("Navigating to http://127.0.0.1:3000...")
        await page.goto("http://127.0.0.1:3000", wait_until="networkidle")
        await asyncio.sleep(2)
        
        title = await page.title()
        print("Page title:", title)
        
        # 截取首页截图确认加载正常
        await page.screenshot(path="scratch/ui_screenshot.png")
        print("Screenshot saved to scratch/ui_screenshot.png")
        
        if errors:
            print("Errors detected:", errors)
        else:
            print("No console errors detected! Frontend is healthy.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_page())
