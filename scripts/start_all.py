import subprocess
import sys
import os
import time
import shutil
import signal

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_EXE = sys.executable

def main():
    print("=" * 65)
    print("   SchemaPulse - 前后端分离全栈一键启动器")
    print("=" * 65)
    print(f"  * 根工程目录: {ROOT_DIR}")
    print(f"  * Python 环境: {PYTHON_EXE}")
    print("  * 后端 API 服务: http://127.0.0.1:8000 (FastAPI + Swagger)")
    print("  * 前端独立控制台: http://127.0.0.1:3000 (Vue 3 + ECharts)")
    print("=" * 65)
    print("正在启动各独立子服务，请稍候...\n")
    sys.stdout.flush()

    backend_script = os.path.join(ROOT_DIR, "backend", "run.py")
    frontend_dir = os.path.join(ROOT_DIR, "frontend")

    processes = []
    try:
        # 1. 启动后端进程
        p_backend = subprocess.Popen(
            [PYTHON_EXE, backend_script],
            cwd=ROOT_DIR
        )
        processes.append(("后端 API 服务", p_backend))
        time.sleep(1.5)

        # 2. 启动前端进程 (Vite DevServer，需要 Node.js >= 18)
        npm_cmd = shutil.which("npm") or shutil.which("npm.cmd")
        if not npm_cmd:
            print("[错误] 未找到 npm 命令，请先安装 Node.js (https://nodejs.org)")
            print("       也可手动进入 frontend/ 目录执行: npm install && npm run dev")
            p_frontend.terminate()
            for name, p in processes:
                p.terminate()
            return
        p_frontend = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=frontend_dir
        )
        processes.append(("前端独立控制台", p_frontend))

        print("\n>>> 前后端子进程均已成功挂起运行！按 Ctrl+C 可一键停止全部服务 <<<\n")
        sys.stdout.flush()

        # 等待子进程
        while True:
            time.sleep(1)
            for name, p in processes:
                poll = p.poll()
                if poll is not None:
                    print(f"[{name}] 异常退出，状态码: {poll}")
                    return

    except KeyboardInterrupt:
        print("\n正在安全终止前后端各子服务...")
        for name, p in processes:
            try:
                p.terminate()
                p.wait(timeout=3)
                print(f"  - [{name}] 已停止")
            except Exception:
                p.kill()
        print("所有服务已安全关闭。")

if __name__ == "__main__":
    main()
