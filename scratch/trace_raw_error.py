from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 注入全局错误捕获
    page.add_init_script("""
    window.addEventListener('error', function(e) {
        console.log('[RAW_ERROR]', e.message, 'at', e.filename, 'line:', e.lineno, 'col:', e.colno);
        if (e.error && e.error.stack) {
            console.log('[STACK]', e.error.stack);
        }
    });
    """)
    
    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
    page.on("pageerror", lambda err: print(f"PAGEERROR: {err}"))
    
    page.goto("http://127.0.0.1:3000", wait_until="commit")
    page.wait_for_timeout(3000)
    browser.close()
