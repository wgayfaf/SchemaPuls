import http.server
import socketserver
import os
import sys

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class DevServerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # 允许跨域与禁止本地开发强缓存，确保前端改动即时生效
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def guess_type(self, path):
        # 确保 js/css 正确的 MIME 类型解析
        if str(path).endswith(".js"):
            return "application/javascript; charset=utf-8"
        if str(path).endswith(".css"):
            return "text/css; charset=utf-8"
        if str(path).endswith(".json"):
            return "application/json; charset=utf-8"
        return super().guess_type(path)

    def log_message(self, format, *args):
        # 格式化输出简要请求日志
        sys.stdout.write(f"[Frontend DevServer] {self.address_string()} - {format % args}\n")
        sys.stdout.flush()

def run_server(port=PORT):
    # 允许地址立即重用
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), DevServerHandler) as httpd:
        print("=" * 60)
        print("   SchemaPulse - 独立前端开发服务 (Frontend DevServer)")
        print("=" * 60)
        print(f"  * 静态托管目录: {DIRECTORY}")
        print(f"  * 本地访问地址: http://127.0.0.1:{port}")
        print(f"  * 局域网地址:   http://localhost:{port}")
        print(f"  * 默认后端路由: http://127.0.0.1:8000")
        print("=" * 60)
        print("提示: 按 Ctrl+C 可安全终止前端服务\n")
        sys.stdout.flush()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[Frontend DevServer] 服务已安全关闭。")

if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else PORT
    run_server(p)
