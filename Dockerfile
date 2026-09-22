# ==========================================================
# SchemaPulse 一体化镜像 (前端静态文件 + 后端 API 单容器)
#
# 构建:  docker build -t schemapulse .
# 运行:  docker run -d --name schemapulse -p 8000:8000 \
#          -v schemapulse-data:/app/data \
#          schemapulse
# 访问:  http://localhost:8000  (前端工作台)
#        http://localhost:8000/docs  (Swagger)
# ==========================================================

# ---------- 阶段 1: 构建前端 ----------
FROM node:20-alpine AS frontend-build
WORKDIR /build

# 先装依赖以利用 Docker 层缓存
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ---------- 阶段 2: 后端运行 ----------
FROM python:3.12-slim

WORKDIR /app/backend

ENV PYTHONUNBUFFERED=1 \
    # 容器内数据库统一放数据卷, 持久化由挂载 /app/data 实现
    SCHEMAPULSE_DB=/app/data/monitor.db \
    # 后端直接托管前端构建产物 (同源访问, 无需跨域)
    FRONTEND_DIST=/app/frontend_dist \
    # 默认时区设置为亚洲/上海 (保证定时调度与日志时区与北京时间一致)
    TZ=Asia/Shanghai

# 安装系统级基础网络与探活工具:
# - iputils-ping: 提供 ping 命令, 用于机器节点物理层 ICMP 探活 (缺失将直接导致机器误判 OFFLINE)
# - curl: 提供 HTTP 测试工具, 用于健康检查与容器排障
# - ca-certificates: 保证 HTTPS 探针 SSL 证书校验正常
# - dnsutils: 提供 dig/nslookup 用于 DNS 域名解析排障
# - tzdata: 设置系统与应用时区
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    curl \
    ca-certificates \
    dnsutils \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend-build /build/dist /app/frontend_dist

RUN mkdir -p /app/data

VOLUME ["/app/data"]
EXPOSE 8000

# 容器原生健康检查 (每 30 秒探测一次系统健康接口)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/dashboard/summary || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
