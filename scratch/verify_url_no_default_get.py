import sys
import shutil

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from playwright.sync_api import sync_playwright

def verify():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        page.on("console", lambda msg: print(f"CONSOLE [{msg.type}]: {msg.text}", flush=True))
        page.on("pageerror", lambda err: print(f"PAGE_ERROR: {err}", flush=True))

        print("1. 打开前端首页...", flush=True)
        page.goto("http://127.0.0.1:3000", wait_until="networkidle", timeout=30000)
        page.wait_for_selector("#app", timeout=15000)
        page.wait_for_function("() => !!window.SchemaPulseApp", timeout=15000)

        print("2. 打开 Postman 风格新建接口探测工作台...", flush=True)
        page.evaluate("() => window.SchemaPulseApp.openCreateApiDialog()")
        page.wait_for_timeout(800)

        # 3. 校验 URL 接口相对路径输入框中的默认值
        print("3. 校验 URL 接口相对路径输入框默认值...", flush=True)
        path_val = page.evaluate("() => window.SchemaPulseApp.apiForm.value.http_path")
        print(f"   当前 apiForm.http_path 初始值: {repr(path_val)}", flush=True)
        assert path_val == "", f"错误：apiForm.http_path 应该默认为空，实际为: {repr(path_val)}"

        input_el = page.locator(".pm-path-input input")
        input_dom_val = input_el.input_value()
        print(f"   当前 URL 输入框 DOM 实际值: {repr(input_dom_val)}", flush=True)
        assert input_dom_val == "", f"错误：输入框 DOM 应该为空，实际为: {repr(input_dom_val)}"
        assert "/get" not in input_dom_val, "错误：输入框仍包含 /get！"

        # 截屏 1: URL 默认清空状态截图
        screenshot_path1 = "scratch/postman_url_empty_path.png"
        page.screenshot(path=screenshot_path1)
        shutil.copy(screenshot_path1, "C:/Users/wgayf/.gemini/antigravity-ide/brain/d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f/postman_url_empty_path.png")
        print("[OK] 已截取 URL 路径默认为空界面: postman_url_empty_path.png", flush=True)

        # 4. 模拟用户输入自定义路径
        print("4. 模拟用户输入自定义路径 /api/v2/orders?status=active...", flush=True)
        input_el.fill("/api/v2/orders?status=active")
        page.wait_for_timeout(400)

        new_path_val = page.evaluate("() => window.SchemaPulseApp.apiForm.value.http_path")
        print(f"   输入后 apiForm.http_path: {new_path_val}", flush=True)
        assert new_path_val == "/api/v2/orders?status=active"

        # 校验 Params 联动解析
        params = page.evaluate("() => window.SchemaPulseApp.apiParamsList.value")
        print("   联动解析出的 Params 列表:", params, flush=True)
        assert any(p["key"] == "status" and p["value"] == "active" for p in params), "Params 联动解析失败！"
        print("[OK] URL 输入与 Params 双向联动解析完美正常！", flush=True)

        # 5. 校验编辑已有接口时的表现
        print("5. 校验编辑接口时不被强行替换为 /get...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.openEditApiDialog({
                id: 888,
                name: "用户详情接口",
                base_url: "http://127.0.0.1:8000",
                http_path: "/api/user/profile",
                http_method: "GET"
            });
        }""")
        page.wait_for_timeout(500)
        edit_path = page.evaluate("() => window.SchemaPulseApp.apiForm.value.http_path")
        print(f"   编辑已有接口时回显路径: {edit_path}", flush=True)
        assert edit_path == "/api/user/profile", f"编辑回显错误，预期 /api/user/profile，实际: {edit_path}"
        print("[OK] 编辑已有接口正确回显真实路径，没有被默认强制覆盖！", flush=True)

        print("\n==========================================")
        print("🎉 全部验证通过！默认路径 /get 已成功去除！")
        print("==========================================")
        browser.close()

if __name__ == "__main__":
    verify()
