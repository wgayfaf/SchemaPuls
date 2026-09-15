import sys
import json

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

        print("1. 打开前端首页...", flush=True)
        page.goto("http://127.0.0.1:3000", timeout=20000)
        page.wait_for_selector("#app", timeout=15000)
        page.wait_for_timeout(1500)

        # 检查 Vue 是否就绪
        is_mounted = page.evaluate("() => !!window.SchemaPulseApp")
        print("Vue 实例挂载状态:", is_mounted, flush=True)
        assert is_mounted, "Vue 实例未就绪！"

        print("2. 打开 Postman 风格工作台并激活 Headers 标签页...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.openCreateApiDialog();
            window.SchemaPulseApp.apiActiveTab.value = 'headers';
        }""")
        page.wait_for_timeout(1000)

        # 截屏 1: Headers 标签页默认展示 (展示系统预填请求头)
        page.screenshot(path="scratch/headers_postman_view.png")
        print("[OK] 已截取工作台 Headers 标签页初始界面: scratch/headers_postman_view.png", flush=True)

        # 3. 验证 Headers 标签页内的 '快速预设' 栏已不复存在
        headers_pane = page.locator("#pane-headers")
        headers_html = headers_pane.inner_html()
        assert "快速预设" not in headers_html, "错误：Headers 标签页内仍存在快速预设！"
        print("[OK] 确认 Headers 标签页内已彻底移除 '快速预设' 栏！", flush=True)

        # 4. 验证系统默认请求头数据
        sys_headers_data = page.evaluate("() => window.SchemaPulseApp.systemDefaultHeaders.value")
        print(f"[OK] 获取到 {len(sys_headers_data)} 个系统默认预填请求头:", flush=True)
        for h in sys_headers_data:
            print(f"     * {h['key']}: {h['value']} ({h['description']})", flush=True)

        keys = [h['key'] for h in sys_headers_data]
        assert "User-Agent" in keys
        assert "Accept" in keys
        assert "Accept-Encoding" in keys
        assert "Connection" in keys
        assert "Host" in keys
        assert "Content-Type" in keys
        assert "Content-Length" in keys

        # 5. 验证 DOM 中显示了 '自动生成' 标识和 '隐藏系统默认请求头' 按钮
        auto_tags = page.locator(".pm-auto-tag")
        assert auto_tags.count() >= 7, f"应有至少 7 个自动生成标签，实际得到 {auto_tags.count()}"
        print(f"[OK] 界面成功渲染 {auto_tags.count()} 个 (自动生成) 标识！", flush=True)

        # 6. 测试折叠系统默认请求头
        print("3. 测试折叠隐藏系统默认请求头...", flush=True)
        page.evaluate("() => { window.SchemaPulseApp.showDefaultHeaders.value = false; }")
        page.wait_for_timeout(500)
        page.screenshot(path="scratch/headers_collapsed_view.png")
        collapsed_tip = page.query_selector(".pm-hidden-headers-tip")
        assert collapsed_tip is not None, "折叠后必须展示快捷提示条！"
        print("[OK] 折叠系统默认请求头后，Postman 风格提示条正常展示！", flush=True)

        # 7. 重新展开默认请求头
        page.evaluate("() => { window.SchemaPulseApp.showDefaultHeaders.value = true; }")
        page.wait_for_timeout(500)

        # 8. 测试自定义请求头输入 User-Agent 触发同名覆盖
        print("4. 测试自定义请求头覆盖 User-Agent...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.apiHeadersList.value = [
                { enabled: true, key: "User-Agent", value: "SchemaPulse-Bot/3.0", description: "自定义覆盖客户端标识" }
            ];
        }""")
        page.wait_for_timeout(600)
        page.screenshot(path="scratch/headers_overridden_view.png")

        # 检查是否标记已被覆盖
        is_overridden = page.evaluate("() => window.SchemaPulseApp.isHeaderOverridden('User-Agent')")
        assert is_overridden is True, "isHeaderOverridden('User-Agent') 应返回 True！"

        override_tag = page.locator(".pm-override-tag")
        assert override_tag.count() >= 1, "界面应渲染 '已被自定义覆盖' 徽章！"
        print("[OK] 自定义请求头成功覆盖同名系统请求头，界面显示划线与覆盖徽章！", flush=True)

        # 9. 验证 getEffectiveHeaders() 结果
        effective = page.evaluate("() => window.SchemaPulseApp.getEffectiveHeaders()")
        print(f"[OK] getEffectiveHeaders() 返回 {len(effective)} 个有效请求头:", flush=True)
        eff_dict = {h['key']: h['value'] for h in effective}
        for k, v in eff_dict.items():
            print(f"     -> {k}: {v}", flush=True)
        assert eff_dict.get("User-Agent") == "SchemaPulse-Bot/3.0", "生效的 User-Agent 必须是自定义的值！"
        assert eff_dict.get("Accept") == "*/*"
        assert eff_dict.get("Connection") == "keep-alive"

        # 10. 验证 Body 切换为 raw (JSON) 时 Content-Type 自动启用
        print("5. 验证 Body 类型联动 Content-Type...", flush=True)
        page.evaluate("() => { window.SchemaPulseApp.apiBodyType.value = 'json'; }")
        page.wait_for_timeout(400)
        effective_json = page.evaluate("() => window.SchemaPulseApp.getEffectiveHeaders()")
        eff_json_dict = {h['key']: h['value'] for h in effective_json}
        assert eff_json_dict.get("Content-Type") == "application/json", "Body 为 JSON 时必须自动注入 Content-Type: application/json！"
        print("[OK] Body 设为 JSON 时 Content-Type 自动激活为 application/json！", flush=True)

        page.screenshot(path="scratch/headers_final_verified.png")
        print("\n🎉🎉🎉 全部 Postman 默认请求头规范功能 100% 验证通过！ 🎉🎉🎉", flush=True)

        browser.close()

if __name__ == "__main__":
    verify()
