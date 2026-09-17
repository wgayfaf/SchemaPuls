"""SchemaPulse 后端应用入口：仅负责 FastAPI 应用创建、中间件、生命周期与路由挂载。

具体业务路由按领域拆分在 app/routers/ 目录下:
  - topology.py      树状拓扑聚合
  - environments.py  环境层 CRUD 与环境变量池
  - groups.py        分组层 CRUD
  - machines.py      机器节点 CRUD / 连通性探测 / 克隆 / 时序指标
  - apis.py          接口探针 CRUD / 即时调试 / 时序指标 / 历史流水
  - tools.py         Schema 推导与校验工具
  - targets.py       旧版平铺目标兼容层与大盘指标
  - postman.py       Postman 数据导入
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.database import init_db
from app.services.scheduler import init_scheduler, scheduler
from app.routers import (
    topology, environments, groups, machines,
    apis, tools, targets, postman, settings,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_scheduler()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="SchemaPulse API",
    description="服务监控资产层级化与解耦探测系统 (前后端分离架构)",
    version="2.0.0",
    lifespan=lifespan
)

# 允许全域跨域 (CORS)，全面支持独立前端工程 (http://127.0.0.1:3000、http://localhost:3000 等)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载各领域路由
app.include_router(topology.router)
app.include_router(environments.router)
app.include_router(groups.router)
app.include_router(machines.router)
app.include_router(apis.router)
app.include_router(tools.router)
app.include_router(targets.router)
app.include_router(postman.router)
app.include_router(settings.router)


@app.get("/")
def read_root():
    """纯后端 API 根路径：返回服务运行元数据及前端服务指引"""
    return {
        "name": "SchemaPulse API Server",
        "version": "2.0.0",
        "status": "online",
        "architecture": "Decoupled (Frontend & Backend Separated)",
        "frontend_dev_url": "http://127.0.0.1:3000",
        "api_docs_url": "/docs",
        "redoc_url": "/redoc"
    }


@app.get("/web")
@app.get("/dashboard")
def get_web_console():
    """向后兼容路由：重定向至独立前端服务"""
    return RedirectResponse(url="http://127.0.0.1:3000")
