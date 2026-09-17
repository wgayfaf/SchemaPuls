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
    FRONTEND_DIST=/app/frontend_dist

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend-build /build/dist /app/frontend_dist

RUN mkdir -p /app/data

VOLUME ["/app/data"]
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
