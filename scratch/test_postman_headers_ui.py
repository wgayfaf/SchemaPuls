import sys
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        errors = []
        page.on("pageerror", lambda err: errors.append(f"PAGE_ERROR: {err}"))
        page.on("console", lambda msg: errors.append(f"CONSOLE_{msg.type}: {msg.text}") if msg.type == "error" else None)

        print("1. 正在访问前端服务...", flush=True)
        page.goto("http://127.0.0.1:3000", wait_until="commit", timeout=10000)
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        page.wait_for_timeout(2000)

        print("2. 打开新建接口工作台 (Postman 风格)...", flush=True)
        # 直接调用 Vue 实例方法确保 100% 稳定展开
        page.evaluate("window.app.openCreateApiDialog()")
        page.wait_for_timeout(800)

        # 截图 1: 工作台打开
        page.screenshot(path="scratch/headers_step1_workbench.png")

        print("3. 切换至 Headers 标签页...", flush=True)
        page.click(".el-tabs__item#tab-headers")
        page.wait_for_timeout(600)

        # 验证快速预设已彻底移除
        content = page.content()
        assert "快速预设" not in content, "错误：'快速预设' 应当已被移除！"
        print("[OK] 确认 '快速预设' 栏已成功移除！", flush=True)

        # 验证系统默认请求头
        headers_table = page.inner_text(".pm-kv-table")
        print("当前 Headers 表格内容预览:\n", headers_table[:250], flush=True)
        assert "User-Agent" in headers_table, "必须包含系统默认 User-Agent"
        assert "Accept" in headers_table, "必须包含系统默认 Accept"
        assert "Connection" in headers_table, "必须包含系统默认 Connection"
        assert "自动生成" in headers_table, "必须展示 (自动生成) 标识"
        print("[OK] 确认 Postman 系统默认请求头全部预填且带有 (自动生成) 标识！", flush=True)

        # 截图 2: 默认请求头展示
        page.screenshot(path="scratch/headers_step2_defaults.png")

        print("4. 测试折叠隐藏默认请求头...", flush=True)
        btn_toggle = page.query_selector(".pm-hidden-headers-btn")
        if btn_toggle:
            btn_toggle.click()
            page.wait_for_timeout(500)
        collapsed_content = page.content()
        assert "已自动携带" in collapsed_content or "已自动启用" in collapsed_content, "折叠后应展示快捷提示条"
        print("[OK] 默认请求头折叠成功，展示 Postman 快捷提示条！", flush=True)
        page.screenshot(path="scratch/headers_step3_collapsed.png")

        print("5. 重新展开默认请求头...", flush=True)
        tip_banner = page.query_selector(".pm-hidden-headers-tip")
        if tip_banner:
            tip_banner.click()
            page.wait_for_timeout(500)

        print("6. 测试输入同名自定义请求头 (触发覆盖与划线效果)...", flush=True)
        key_input = page.query_selector("input[placeholder*='Authorization']")
        if key_input:
            key_input.fill("User-Agent")
            page.wait_for_timeout(400)
        val_input = page.query_selector("input[placeholder*='变量引用']")
        if val_input:
            val_input.fill("MyCustomBot/2.0")
            page.wait_for_timeout(400)

        override_text = page.content()
        assert "已被自定义覆盖" in override_text, "输入同名 User-Agent 后应展示 '已被自定义覆盖' 徽章"
        print("[OK] 输入同名 User-Agent 后成功触发 '已被自定义覆盖' 划线与提示徽章！", flush=True)
        page.screenshot(path="scratch/headers_step4_override.png")

        print("7. 测试切换 Body 类型为 raw (JSON) 动态联动 Content-Type...", flush=True)
        page.click(".el-tabs__item#tab-body")
        page.wait_for_timeout(400)
        page.click("label.el-radio-button:has-text('raw (JSON)')")
        page.wait_for_timeout(400)
        # 切回 Headers 检查
        page.click(".el-tabs__item#tab-headers")
        page.wait_for_timeout(400)
        updated_table = page.inner_text(".pm-kv-table")
        assert "application/json" in updated_table, "Body为JSON时，Content-Type 应当自动联动为 application/json"
        print("[OK] Body 设为 JSON 时 Content-Type 自动联动 application/json 成功！", flush=True)
        page.screenshot(path="scratch/headers_step5_body_json.png")

        print("控制台报错记录:", errors, flush=True)
        assert len(errors) == 0, f"发现控制台或页面错误: {errors}"
        print("🎉🎉🎉 全部 Postman 默认请求头功能 100% 验证通过！ 🎉🎉🎉", flush=True)

        browser.close()

if __name__ == "__main__":
    main()
