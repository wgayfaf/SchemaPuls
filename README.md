# SchemaPulse - 服务健康与结构变更监控系统

基于 FastAPI 异步引擎与 Vue 3 的轻量级高并发服务质量探测（APM/Synthetics）系统。

---

## 📚 文档导航

* [技术选型与实现方案.md](file:///c:/Users/wgayf/Desktop/wuyu/SchemaPulse/%E6%8A%80%E6%9C%AF%E9%80%89%E5%9E%8B%E4%B8%8E%E5%AE%9E%E7%8E%B0%E6%96%B9%E6%A1%88.md)：详细分析前端与后端的选型依据、实现方向、架构模块连接关系及分阶段开发任务。
* [架构与开发计划.md](file:///c:/Users/wgayf/Desktop/wuyu/SchemaPulse/%E6%9E%B6%E6%9E%84%E4%B8%8E%E5%BC%80%E5%8F%91%E8%AE%A1%E5%88%92.md)：系统总体架构图、拓扑关系、防抖降噪机制与分阶段里程碑。
* [文档.md](file:///c:/Users/wgayf/Desktop/wuyu/SchemaPulse/%E6%96%87%E6%A1%A3.md)：原始需求与前后端代码开发规范。

---

## 🚀 原型快速运行指南

### 方式 1：运行阶段 0 独立探针验证脚本 (MVP Script)
验证底层 TCP 探活、HTTP 请求、Schema 破坏性变更捕获及邮件告警模板：
```bash
python scripts/standalone_probe.py
```

### 方式 2：运行阶段 1 自动化全流程回归测试
验证 FastAPI + SQLite + 动态调度器 + Schema 推导 + 即时探测的完整闭环：
```bash
python tests/verify_prototype.py
```

### 方式 3：启动后端 Web 服务并打开可视化控制台
启动服务：
```bash
python backend/run.py
```
启动后在浏览器打开：
* **现代化监控控制台 (Vue 3 + Element Plus + ECharts)**：**[http://127.0.0.1:8000/web](http://127.0.0.1:8000/web)**
* 交互式接口文档 (Swagger UI)：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* 根路径自动重定向：[http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### 方式 4：运行前端控制台与时序报表回归测试
```bash
python tests/verify_frontend.py
```

---

## 📂 项目工程结构

```
SchemaPulse/
├── backend/                  # 后端服务
│   ├── app/
│   │   ├── database.py       # SQLite 连接与会话管理
│   │   ├── models.py         # SQLModel 数据模型 (Target, History)
│   │   ├── services/
│   │   │   ├── probe_service.py # 探针核心执行逻辑与状态机判定
│   │   │   └── scheduler.py     # APScheduler 动态定时任务
│   │   └── main.py           # FastAPI 入口与 RESTful 路由
│   └── run.py                # 后端一键启动入口
├── scripts/
│   └── standalone_probe.py   # 阶段 0 独立探针最小验证脚本
├── tests/
│   └── verify_prototype.py   # 阶段 1 自动化集成测试脚本
├── 技术选型与实现方案.md       # 前后端技术选型与实现逻辑说明
├── 架构与开发计划.md           # 总体架构设计与推进计划
└── README.md
```
