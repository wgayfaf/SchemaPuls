from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlmodel import SQLModel, Field, JSON, Column


# ==========================================================
# 四层资产模型：环境 -> 分组 -> 机器节点 -> 接口探针
# ==========================================================

class Environment(SQLModel, table=True):
    """第一层：运行环境 (如: 生产环境, 预发布环境, 测试环境)"""
    __tablename__ = "environments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=64, unique=True, index=True)
    description: Optional[str] = Field(default=None, max_length=255)
    base_url: Optional[str] = Field(default=None, max_length=255) # 环境默认前置服务 URL (如 https://api.example.com)
    order_num: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ServiceGroup(SQLModel, table=True):
    """第二层：业务分组/微服务集群 (隶属于环境)"""
    __tablename__ = "service_groups"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    environment_id: int = Field(foreign_key="environments.id", index=True)
    name: str = Field(max_length=64, index=True)
    description: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MachineNode(SQLModel, table=True):
    """第三层：机器节点/实例 (隶属于分组，承载 TCP 端口连通性及网络延时探测)"""
    __tablename__ = "machine_nodes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="service_groups.id", index=True)
    name: str = Field(max_length=64, index=True)
    host: str = Field(max_length=255, index=True)       # IP 或域名
    port: int = Field(index=True)                       # TCP 端口
    base_url: Optional[str] = Field(default=None, max_length=255) # 机器服务基准地址 (如 https://api.prod.com 或 http://192.168.1.10:8080)
    cron_interval_minutes: int = Field(default=5)       # 端口探活周期
    is_active: bool = Field(default=True)
    
    # 告警与防抖配置
    retry_threshold: int = Field(default=3)             # 连续不可达 N 次触发告警
    silence_minutes: int = Field(default=30)            # 告警冷却时间
    email_receivers: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # 运行状态与指标
    current_status: str = Field(default="UNKNOWN")      # ONLINE, OFFLINE, DEGRADED, UNKNOWN
    consecutive_failures: int = Field(default=0)
    ping_ok: Optional[bool] = None                      # 主机 Ping (ICMP) 连通状态
    last_ping_latency_ms: Optional[float] = None        # 最新主机 Ping 延时(ms)
    tcp_ok: Optional[bool] = None                       # 服务端口 (TCP) 连通状态
    last_tcp_latency_ms: Optional[float] = None         # 最新 TCP 握手延时(ms)
    last_error_message: Optional[str] = None            # 最近探活诊断或错误明细
    last_probed_at: Optional[datetime] = None
    last_alert_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApiProbe(SQLModel, table=True):
    """第四层：接口探针 (隶属于机器，继承机器 host:port，承载 HTTP 状态码与 Schema 结构校验)"""
    __tablename__ = "api_probes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    machine_id: int = Field(foreign_key="machine_nodes.id", index=True)
    name: str = Field(max_length=64, index=True)
    base_url: Optional[str] = Field(default=None, max_length=255) # 自定义前置基准地址 (如 https://api.prod.com，优先于宿主机器地址)
    http_path: str = Field(default="/health")           # 业务接口路径
    http_method: str = Field(default="GET")
    http_params: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON)) # 查询参数列表
    http_headers: Any = Field(default=[], sa_column=Column(JSON)) # 请求头列表或字典
    http_body_type: str = Field(default="none")                                   # none, json, form_data, raw
    http_body: Optional[str] = Field(default=None)                                # 请求体内容
    auth_type: str = Field(default="none")                                        # none, bearer, basic
    auth_config: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))       # 鉴权配置，如 token 或 basic 凭证
    expected_schema: Dict[str, Any] = Field(sa_column=Column(JSON)) # Draft-7 JSON Schema
    pre_actions: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON)) # 前置操作 (变量定义/请求头注入/参数注入/前置脚本)
    post_actions: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON)) # 后置操作 (状态码断言/耗时断言/JSONPath断言/变量提取)
    cron_interval_minutes: int = Field(default=5)
    is_active: bool = Field(default=True)
    
    # 告警配置
    retry_threshold: int = Field(default=3)
    silence_minutes: int = Field(default=30)
    email_receivers: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # 运行状态与指标 (支持熔断短路状态 CIRCUIT_BROKEN)
    current_status: str = Field(default="UNKNOWN")      # HEALTHY, DOWN, DEGRADED, CIRCUIT_BROKEN, UNKNOWN
    consecutive_failures: int = Field(default=0)
    last_http_code: Optional[int] = None
    last_http_latency_ms: Optional[float] = None
    last_schema_matched: Optional[bool] = None
    last_probed_at: Optional[datetime] = None
    last_alert_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ==========================================================
# 分离的历史探测流水记录
# ==========================================================

class MachineProbeHistory(SQLModel, table=True):
    """机器节点探活历史 (Ping 主机探活 + TCP 端口探活)"""
    __tablename__ = "machine_probe_histories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    machine_id: int = Field(foreign_key="machine_nodes.id", index=True)
    ping_ok: bool = Field(default=False)
    ping_latency_ms: Optional[float] = None
    tcp_ok: bool = Field(default=False)
    tcp_latency_ms: Optional[float] = None
    error_message: Optional[str] = None
    probed_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ApiProbeHistory(SQLModel, table=True):
    """接口探针业务契约校验历史"""
    __tablename__ = "api_probe_histories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    api_probe_id: int = Field(foreign_key="api_probes.id", index=True)
    machine_id: int = Field(foreign_key="machine_nodes.id", index=True)
    circuit_broken: bool = Field(default=False)         # 是否因宿主机器离线而熔断跳过
    http_status_code: Optional[int] = None
    http_latency_ms: Optional[float] = None
    schema_matched: bool = Field(default=False)
    schema_diff_detail: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    assertions_result: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON)) # 后置操作断言对比明细
    raw_response_snippet: Optional[str] = None
    is_healthy: bool = Field(default=False, index=True)
    probed_at: datetime = Field(default_factory=datetime.utcnow, index=True)


# ==========================================================
# 向下兼容旧版单层平铺模型 (保留供历史数据迁移)
# ==========================================================

class MonitorTarget(SQLModel, table=True):
    __tablename__ = "monitor_targets"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=64, index=True)
    group_name: str = Field(default="生产环境", max_length=64, index=True)
    host: str = Field(max_length=255)
    port: int
    http_path: str = Field(default="/health")
    http_method: str = Field(default="GET")
    http_headers: Dict[str, str] = Field(default={}, sa_column=Column(JSON))
    expected_schema: Dict[str, Any] = Field(sa_column=Column(JSON))
    cron_interval_minutes: int = Field(default=5)
    is_active: bool = Field(default=True)
    
    retry_threshold: int = Field(default=3)
    silence_minutes: int = Field(default=30)
    wechat_webhook: Optional[str] = None
    email_receivers: List[str] = Field(default=[], sa_column=Column(JSON))
    
    current_status: str = Field(default="UNKNOWN")
    consecutive_failures: int = Field(default=0)
    last_latency_ms: Optional[float] = None
    last_tcp_latency_ms: Optional[float] = None
    last_http_latency_ms: Optional[float] = None
    last_probed_at: Optional[datetime] = None
    last_alert_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProbeHistory(SQLModel, table=True):
    __tablename__ = "probe_histories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    target_id: int = Field(foreign_key="monitor_targets.id", index=True)
    tcp_ok: bool
    tcp_latency_ms: Optional[float] = None
    http_status_code: Optional[int] = None
    http_latency_ms: Optional[float] = None
    schema_matched: bool
    schema_diff_detail: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))
    raw_response_snippet: Optional[str] = None
    is_healthy: bool = Field(index=True)
    probed_at: datetime = Field(default_factory=datetime.utcnow, index=True)
