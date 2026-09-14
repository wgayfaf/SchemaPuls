import os
import sys
import time
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

    # 3. 验证独立前端目录工程完整性
    required_frontend_files = [
        "index.html",
        "config.js",
        os.path.join("css", "style.css"),
        os.path.join("js", "app.js"),
        "run.py",
        "package.json"
    ]
    for rel_path in required_frontend_files:
        full_path = os.path.join(frontend_dir, rel_path)
        assert os.path.exists(full_path), f"缺少前端工程核心文件: {rel_path}"
        assert os.path.getsize(full_path) > 0, f"前端文件为空: {rel_path}"
    print(f"[OK] [3/5] 独立前端工程目录 (frontend/) 结构完整（含 CSS 样式抽离、JS 驱动、全局配置）")

    # 4. 验证前端全局配置与 Axios 跨域注入
    with open(os.path.join(frontend_dir, "config.js"), "r", encoding="utf-8") as f:
        config_code = f.read()
        assert "API_BASE_URL" in config_code
    with open(os.path.join(frontend_dir, "js", "app.js"), "r", encoding="utf-8") as f:
        js_code = f.read()
        assert "axios.defaults.baseURL" in js_code
    print("[OK] [4/5] 前端 Axios 全局跨域 baseURL 与动态配置注入正常")

    # 5. 启动独立前端 DevServer 并发起 HTTP 请求探测 (3000 端口)
    dev_server_path = os.path.join(frontend_dir, "run.py")
    p_dev = subprocess.Popen([sys.executable, dev_server_path, "3001"], cwd=frontend_dir)
    time.sleep(1.5)
    try:
        resp_fe = requests.get("http://127.0.0.1:3001/")
        assert resp_fe.status_code == 200
        assert "SchemaPulse" in resp_fe.text
        assert "style.css" in resp_fe.text
        assert "config.js" in resp_fe.text
        assert resp_fe.headers.get("Access-Control-Allow-Origin") == "*"
        print("[OK] [5/5] 前端独立 DevServer (Port: 3001) 托管验证 100% 成功！CORS 响应头与静态外链均正确")
    finally:
        p_dev.terminate()
        p_dev.wait(timeout=3)

    print("\n>>> 前后端分离架构全面验证 100% 通过！<<<\n")

if __name__ == "__main__":
    test_decoupled_architecture()
