import uvicorn
import os
import sys

# 将 backend 加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("Starting SchemaPulse Backend Service at http://127.0.0.1:8000 ...")
    print("Web Console available at: http://127.0.0.1:8000/web")
    print("API Documentation available at: http://127.0.0.1:8000/docs")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
