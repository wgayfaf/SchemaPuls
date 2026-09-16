import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 900})
        await page.goto("http://127.0.0.1:3000/")
        await page.wait_for_timeout(2000)

        # 1. 切换至【环境管理】页面查看环境变量池列
        await page.evaluate("() => { const app = document.querySelector('#app')?.__vue_app__; }")
        env_menu = page.locator("text=环境管理").first
        if await env_menu.count() > 0:
            await env_menu.click()
            await page.wait_for_timeout(1500)
            await page.screenshot(path="env_management_after_fix.png")
            print("Saved env_management_after_fix.png")

            # 点击变量管理按钮
            var_btn = page.locator("button:has-text('变量管理')").first
            if await var_btn.count() > 0:
                await var_btn.click()
                await page.wait_for_timeout(1000)
                await page.screenshot(path="env_dialog_after_fix.png")
                print("Saved env_dialog_after_fix.png")

        # 2. 切换至【接口管理】工作台
        api_menu = page.locator("text=接口管理").first
        if await api_menu.count() > 0:
            await api_menu.click()
            await page.wait_for_timeout(1500)
            # 点击编辑或新建接口
            edit_btn = page.locator("button:has-text('编辑')").first
            if await edit_btn.count() > 0:
                await edit_btn.click()
                await page.wait_for_timeout(1000)
                # 点击顶部环境变量池按钮
                env_badge = page.locator(".pm-env-badge").first
                if await env_badge.count() > 0:
                    await env_badge.click()
                    await page.wait_for_timeout(1000)
                    await page.screenshot(path="workbench_env_dialog_after_fix.png")
                    print("Saved workbench_env_dialog_after_fix.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
