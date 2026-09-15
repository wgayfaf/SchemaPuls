import sys
import json
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

        # 3. 验证初始状态：系统默认请求头正常情况下不自动展开！
        print("3. 验证初始状态：系统默认请求头必须默认收起/折叠...", flush=True)
        show_headers = page.evaluate("() => window.SchemaPulseApp.showDefaultHeaders.value")
        print("   showDefaultHeaders 初始值:", show_headers, flush=True)
        assert show_headers is False, "错误：新建工作台时 showDefaultHeaders 应该默认为 False (不自动展开)！"

        # 验证 DOM：此时默认请求头未展开（auto_tag 数量为 0），折叠提示条可见
        auto_tags_count = page.locator(".pm-auto-tag").count()
        print(f"   未展开状态下系统请求头标签数: {auto_tags_count} (预期为 0)", flush=True)
        assert auto_tags_count == 0, f"初始状态下不应渲染系统请求头，但找到了 {auto_tags_count} 个！"

        tip_el = page.locator(".pm-hidden-headers-tip")
        assert tip_el.is_visible(), "折叠状态下快捷提示条必须可见！"
        tip_text = tip_el.inner_text()
        print("   快捷提示条文案:", tip_text.replace('\n', ' '), flush=True)

        btn_text = page.locator(".pm-hidden-headers-btn").inner_text()
        print("   折叠按钮文案:", btn_text.replace('\n', ' '), flush=True)
        assert "7 个系统默认请求头 (已自动携带)" in btn_text, f"按钮文案不符合预期: {btn_text}"

        # 截屏 1: 默认初始状态 (折叠收起)
        page.screenshot(path="scratch/postman_headers_default_collapsed.png")
        shutil.copy("scratch/postman_headers_default_collapsed.png", "C:/Users/wgayf/.gemini/antigravity-ide/brain/d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f/postman_headers_default_collapsed.png")
        print("[OK] 已截取初始折叠状态截图: postman_headers_default_collapsed.png", flush=True)

        # 4. 模拟用户主动点击展开
        print("4. 模拟用户点击快捷提示条进行展开...", flush=True)
        tip_el.click()
        page.wait_for_timeout(600)

        show_headers_after_click = page.evaluate("() => window.SchemaPulseApp.showDefaultHeaders.value")
        print("   点击后 showDefaultHeaders 值:", show_headers_after_click, flush=True)
        assert show_headers_after_click is True, "点击展开后 showDefaultHeaders 必须为 True！"

        auto_tags_after = page.locator(".pm-auto-tag").count()
        print(f"   展开后系统默认请求头标签数: {auto_tags_after} (预期 >= 7)", flush=True)
        assert auto_tags_after >= 7, f"展开后应渲染出至少 7 个系统请求头，实际: {auto_tags_after}"

        # 截屏 2: 用户点击展开后的状态
        page.screenshot(path="scratch/postman_headers_user_expanded.png")
        shutil.copy("scratch/postman_headers_user_expanded.png", "C:/Users/wgayf/.gemini/antigravity-ide/brain/d0e04d8e-67f2-4725-9c9a-b4c6d53d0f1f/postman_headers_user_expanded.png")
        print("[OK] 已截取用户点击展开后截图: postman_headers_user_expanded.png", flush=True)

        # 5. 模拟用户点击按钮再次折叠
        print("5. 模拟用户点击 '隐藏系统默认请求头' 按钮再次折叠...", flush=True)
        page.locator(".pm-hidden-headers-btn").click()
        page.wait_for_timeout(500)
        show_headers_recollapse = page.evaluate("() => window.SchemaPulseApp.showDefaultHeaders.value")
        assert show_headers_recollapse is False, "再次点击应切换回折叠状态！"
        print("[OK] 再次点击切换按钮成功收起！", flush=True)

        # 6. 验证未展开/折叠状态下发包聚合 engine
        print("6. 验证折叠状态下发包 engine 是否依然正常自动携带默认请求头...", flush=True)
        effective = page.evaluate("() => window.SchemaPulseApp.getEffectiveHeaders()")
        eff_dict = {h['key']: h['value'] for h in effective}
        print(f"[OK] getEffectiveHeaders() 聚合获取到 {len(effective)} 个有效请求头:", flush=True)
        for k, v in eff_dict.items():
            print(f"     -> {k}: {v}", flush=True)

        assert "User-Agent" in eff_dict, "必须包含 User-Agent！"
        assert "Accept" in eff_dict, "必须包含 Accept！"
        assert "Accept-Encoding" in eff_dict, "必须包含 Accept-Encoding！"
        assert "Connection" in eff_dict, "必须包含 Connection！"
        assert eff_dict["Connection"] == "keep-alive"

        # 7. 测试自定义同名覆盖
        print("7. 测试自定义请求头覆盖...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.showDefaultHeaders.value = true;
            window.SchemaPulseApp.apiHeadersList.value = [
                { enabled: true, key: "User-Agent", value: "SchemaPulse-Bot/Custom", description: "覆盖客户端标识" }
            ];
        }""")
        page.wait_for_timeout(500)
        is_overridden = page.evaluate("() => window.SchemaPulseApp.isHeaderOverridden('User-Agent')")
        assert is_overridden is True, "isHeaderOverridden('User-Agent') 应返回 True！"
        effective_after_cov = page.evaluate("() => window.SchemaPulseApp.getEffectiveHeaders()")
        eff_cov_dict = {h['key']: h['value'] for h in effective_after_cov}
        assert eff_cov_dict["User-Agent"] == "SchemaPulse-Bot/Custom", "User-Agent 必须被自定义值覆盖！"
        print(f"[OK] 覆盖后的 User-Agent: {eff_cov_dict['User-Agent']}", flush=True)

        # 8. 测试编辑已有接口探测时，默认也是折叠状态
        print("8. 测试编辑接口时，Headers 是否默认也是折叠状态...", flush=True)
        page.evaluate("""() => {
            window.SchemaPulseApp.openEditApiDialog({
                id: 9999,
                name: "测试编辑接口",
                method: "GET",
                target_url: "http://127.0.0.1:8000/api/health",
                http_headers: [{ enabled: true, key: "X-Custom", value: "123", description: "" }]
            });
            window.SchemaPulseApp.apiActiveTab.value = 'headers';
        }""")
        page.wait_for_timeout(500)
        edit_show_headers = page.evaluate("() => window.SchemaPulseApp.showDefaultHeaders.value")
        print("   编辑接口打开时 showDefaultHeaders 值:", edit_show_headers, flush=True)
        assert edit_show_headers is False, "编辑接口打开时 showDefaultHeaders 也必须默认为 False！"
        print("[OK] 编辑接口场景下 Headers 系统默认请求头同样保持默认折叠！", flush=True)

        print("\n==========================================")
        print("🎉 全部验证通过！系统默认请求头已完美实现默认折叠，用户点击才展开！")
        print("==========================================")
        browser.close()

if __name__ == "__main__":
    verify()
