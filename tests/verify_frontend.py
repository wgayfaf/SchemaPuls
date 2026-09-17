import os
import sys
import time
import shutil
import subprocess
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(root_dir, "backend")
frontend_dir = os.path.join(root_dir, "frontend")
sys.path.insert(0, backend_dir)

from app.main import app

def test_decoupled_architecture():
    print("==================================================")
    print("   SchemaPulse - 前后端分离架构全面联调验证")
    print("==================================================")

    # 1. 验证后端纯净 API 根节点与元数据
    with TestClient(app) as client:
        resp_root = client.get("/")
        assert resp_root.status_code == 200
        data = resp_root.json()
        assert data.get("status") == "online"
        assert "Decoupled" in data.get("architecture", "")
        print("[OK] [1/5] 后端纯净 API 根路径 (/) 正确返回前后端分离运行元数据:")
        print(f"      - 服务名称: {data.get('name')}")
        print(f"      - 架构模式: {data.get('architecture')}")
        print(f"      - 前端地址: {data.get('frontend_dev_url')}")

        # 2. 验证核心业务 API (大盘统计) 正常响应
        resp_summary = client.get("/api/dashboard/summary")
        assert resp_summary.status_code == 200
        summary_data = resp_summary.json()
        print(f"[OK] [2/5] 业务 API (/api/dashboard/summary) 正常返回，监控目标数: {summary_data['total_targets']}")

    # 3. 验证独立前端 Vite 工程完整性 (新版工程化结构)
    required_frontend_files = [
        "index.html",
        "vite.config.js",
        "package.json",
        os.path.join("src", "main.js"),
        os.path.join("src", "App.vue"),
        os.path.join("src", "workbench.js"),
        os.path.join("src", "style.css"),
    ]
    for rel_path in required_frontend_files:
        full_path = os.path.join(frontend_dir, rel_path)
        assert os.path.exists(full_path), f"缺少前端工程核心文件: {rel_path}"
        assert os.path.getsize(full_path) > 0, f"前端文件为空: {rel_path}"
    print(f"[OK] [3/5] 独立前端 Vite 工程 (frontend/) 结构完整（含 App.vue、workbench.js、style.css）")

    # 4. 验证 Axios 全局配置与 API 代理注入
    with open(os.path.join(frontend_dir, "vite.config.js"), "r", encoding="utf-8") as f:
        vite_code = f.read()
        assert "127.0.0.1:8000" in vite_code
        assert "proxy" in vite_code
    with open(os.path.join(frontend_dir, "src", "workbench.js"), "r", encoding="utf-8") as f:
        js_code = f.read()
        assert "axios.defaults.baseURL" in js_code
    print("[OK] [4/5] 前端 Axios baseURL 与 Vite 开发代理配置正常")

    # 5. 启动 Vite DevServer 并发起 HTTP 请求探测 (3000 端口)
    npm_cmd = shutil.which("npm") or shutil.which("npm.cmd")
    assert npm_cmd, "未找到 npm，请先安装 Node.js (>=18)"
    p_dev = subprocess.Popen([npm_cmd, "run", "dev"], cwd=frontend_dir,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(6)
    try:
        resp_fe = requests.get("http://127.0.0.1:3000/")
        assert resp_fe.status_code == 200
        assert "SchemaPulse" in resp_fe.text
        assert "/src/main.js" in resp_fe.text
        print("[OK] [5/5] 前端 Vite DevServer (Port: 3000) 托管验证 100% 成功！")
    finally:
        p_dev.terminate()
        p_dev.wait(timeout=3)

    print("\n>>> 前后端分离架构全面验证 100% 通过！<<<\n")

if __name__ == "__main__":
    test_decoupled_architecture()
