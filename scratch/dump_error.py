import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        def on_page_error(err):
            print("PAGE ERROR:", err)
            if hasattr(err, "stack"):
                print("STACK:", err.stack)
        def on_console(msg):
            print(f"CONSOLE {msg.type}: {msg.text}")
            if msg.location:
                print(f"  LOCATION: {msg.location}")
                
        page.on("pageerror", on_page_error)
        page.on("console", on_console)
        
        await page.goto("http://127.0.0.1:3000", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
