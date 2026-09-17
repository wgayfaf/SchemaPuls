# SchemaPulse - 服务健康巡检与接口契约变更监控系统

<p align="center">
  <strong>基于 FastAPI 异步引擎、QuickJS 内存沙箱与 Vue 3 的四层资产解耦、离线熔断与接口契约巡检平台</strong>
</p>

---

## 📚 核心文档导航

* 📘 **[技术选型与实现方案.md](file:///c:/Users/wgayf/Desktop/wuyu/SchemaPulse/%E6%8A%80%E6%9C%AF%E9%80%89%E5%9E%8B%E4%B8%8E%E5%AE%9E%E7%8E%B0%E6%96%B9%E6%A1%88.md)**：详细论述 FastAPI、QuickJS、SQLModel、SQLite WAL 读写分离、双重探活机制与 JS 加密套件的技术选型对比与代码实现方案。
* 📐 **[系统架构设计文档.md](file:///c:/Users/wgayf/Desktop/wuyu/SchemaPulse/%E7%B3%BB%E7%BB%9F%E6%9E%B6%E6%9E%84%E8%AE%BE%E8%AE%A1%E6%96%87%E6%A1%A3.md)**：系统六层全景架构、四层拓扑类图、Mermaid ER 实体模型、探活/熔断时序图、沙箱执行时序图与高可用演进路线。

---

## 🌟 核心特性

1. **四层资产拓扑解耦**：
   - 划分 **环境 (Environment) $\rightarrow$ 服务分组 (ServiceGroup) $\rightarrow$ 机器节点 (MachineNode) $\rightarrow$ 接口探针 (ApiProbe)** 四层结构，支持全局环境变量池与三级级联 Base URL 覆盖决议。
2. **主机(Ping) + 服务端口(TCP) 双阶段探活**：
   - ICMP 系统 Ping 探活结合 TCP 端口握手，精准区分 **ONLINE**（正常在线）、**DEGRADED**（主机在线但服务未开启/未监听）与 **OFFLINE**（主机离线宕机），彻底避免虚拟网卡假连通误判。
3. **离线熔断短路防护 (Circuit Breaker)**：
   - 宿主机器宕机时自动触发熔断机制，名下接口探针微秒级标记为 `CIRCUIT_BROKEN`，完全跳过无效网络 I/O，杜绝连接池堵塞与告警风暴；机器恢复时自动解除熔断。
4. **QuickJS 纯净脚本沙箱与加解密套件**：
   - 内嵌轻量级 QuickJS 引擎执行 Pre-request Script 与 Tests 后置断言脚本；
   - 内置 Web API Polyfill（`btoa`、`atob`、`Buffer`）与完整加密套件（`CryptoJS`、`jsrsasign`），原生支持 RSA 签名验签、AES/MD5/HmacSHA256 加密及 JWT 解析。
5. **Postman / Apifox 格式无缝导入**：
   - 兼容导入 Postman Collection v2.1 格式，支持 Headers、Query Params、Body（Raw JSON / Form-Data）、鉴权配置与脚本，支持一键批量克隆接口至多台机器节点。
6. **动态宏引擎与路径参数智能匹配**：
   - 支持 `{{$timestamp}}`、`{{$uuid}}`、`{{$randomInt(1, 100)}}`、`{{variable}}` 宏插值，自动匹配并替换 `/:param` 与 `/{param}` 路径参数。
7. **JSON Schema 契约校验与破坏性检测**：
   - 基于 Draft-7 规范自动推断并比对响应结构，精准捕获必填字段缺失、数据类型漂移及未声明新增字段。
8. **时序排障仪表盘与降噪告警**：
   - ECharts 时序延时折线图、可用度大盘，具备连续失败阈值防抖（Retry Threshold）与冷却静默（Silence Minutes）机制，支持 HTML 富文本邮件告警与自动恢复通知。
9. **灵活自定义探测周期**：
   - 支持 1m 至 43200m（最长 30 天）自定义探活周期，或一键关闭自动探测转为“纯手动/被动巡检”。

---

## 🚀 快速启动指南

### 1. 环境准备
* Python 3.11+ 或 3.12
* 依赖库安装：
  ```bash
  pip install fastapi uvicorn httpx sqlmodel jsonschema genson apscheduler quickjs
  ```

### 2. 一键启动服务 (推荐)
在项目根目录下执行统一启动脚本，将自动并发拉起后端 API 服务与前端 SPA 服务：
```bash
python start_all.py
```
启动成功后，浏览器直接访问：
* 🖥️ **前端交互控制台**：**[http://127.0.0.1:3000](http://127.0.0.1:3000)**
* 🔌 **后端 API Swagger 文档**：**[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**
* 📖 **ReDoc 文档**：[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 3. 分别单独启动
* **仅启动后端服务**（监听 8000 端口）：
  ```bash
  python backend/run.py
  ```
* **仅启动前端服务**（监听 3000 端口）：
  ```bash
  python frontend/run.py
  ```

---

## 🧪 自动化测试套件

项目在 `tests/` 目录内置了覆盖各核心子系统的端到端自动化测试：
```bash
# 验证四层拓扑、解耦探测、熔断短路与批量克隆
python tests/verify_hierarchical.py

# 验证机器主机(Ping) + 端口(TCP) 双阶段探活
python tests/verify_dual_probe.py

# 验证前置与后置操作 (Pre/Post Actions) 及动态环境变量
python tests/verify_pre_post_actions.py

# 验证 Postman 导入与解析引擎
python tests/verify_postman_import.py
```

---

## 📂 项目工程目录结构

```
SchemaPulse/
├── backend/                       # 后端服务源码
│   ├── run.py                     # 后端独立启动入口 (Uvicorn 8000)
│   ├── monitor.db                 # SQLite 生产数据库 (WAL 模式)
│   └── app/
│       ├── database.py            # SQLite 连接配置、PRAGMA WAL 调优与自动迁移
│       ├── models.py              # 四层资产模型与历史流水表结构定义
│       ├── main.py                # FastAPI 路由、拓扑树聚合与 RESTful API
│       └── services/
│           ├── probe_service.py   # 核心探活引擎 (Ping/TCP/HTTP/熔断守卫/契约比对)
│           ├── action_engine.py   # QuickJS 动态沙箱、pm.* 注入与环境变量同步
│           ├── template_engine.py # 宏变量渲染与路径参数解析器
│           ├── postman_importer.py# Postman v2.1 递归解析与导入引擎
│           ├── scheduler.py       # APScheduler 任务调度与周期动态管理
│           ├── email_service.py   # 邮件通知、防抖降噪与 HTML 告警模板
│           ├── metric_service.py  # 历史时序监控指标聚合服务
│           └── js_libs/           # 沙箱内置 JS 库 (crypto-js, jsrsasign)
├── frontend/                      # 前端 SPA 页面与静态资源
│   ├── run.py                     # 前端静态服务启动入口 (Port 3000)
│   ├── index.html                 # Vue 3 + Element Plus + ECharts 仪表盘骨架
│   ├── css/
│   │   └── style.css              # 现代化深色运维仪表盘定制样式
│   └── js/
│       └── app.js                 # 前端核心业务控制器 (拓扑大盘/调试工作台/导入交互)
├── scripts/
│   ├── start_all.py               # 跨平台一键前后端守护启动脚本
│   └── standalone_probe.py        # 独立最小化探活脚本
├── tests/                         # 自动化回归测试套件
│   ├── verify_hierarchical.py     # 四层架构与熔断全流程验证
│   ├── verify_dual_probe.py       # Ping + TCP 双重探活验证
│   └── ...                        # 其他专项测试脚本
├── .gitignore                     # Git 忽略配置文件
├── 技术选型与实现方案.md            # 技术选型论证与实现方案规范
├── 系统架构设计文档.md              # 系统全景分层、UML类图、ERD与流程时序
└── README.md                      # 项目入口说明文档
```
