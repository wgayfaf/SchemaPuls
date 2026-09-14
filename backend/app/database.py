from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy import text
import os

DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DB_DIR, "monitor.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

from sqlalchemy import text, event

# 原型阶段使用 SQLite，connect_args 适配并发与高吞吐
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 15}
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=15000;")
    finally:
        cursor.close()



def init_db():
    """初始化数据库表并执行轻量迁移"""
    from app.models import (
        Environment, ServiceGroup, MachineNode, ApiProbe,
        MachineProbeHistory, ApiProbeHistory,
        MonitorTarget, ProbeHistory
    )
    # 创建所有四层模型新表以及兼容表
    SQLModel.metadata.create_all(engine)
    
    # 兼容历史老字段迁移
    with engine.connect() as conn:
        columns_to_add = [
            ("group_name", "VARCHAR(64) DEFAULT '生产环境'"),
            ("last_latency_ms", "FLOAT"),
            ("last_tcp_latency_ms", "FLOAT"),
            ("last_http_latency_ms", "FLOAT"),
            ("last_probed_at", "DATETIME"),
        ]
        for col_name, col_def in columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE monitor_targets ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except Exception:
                pass  # 若字段已存在则忽略异常

        api_columns_to_add = [
            ("http_params", "TEXT DEFAULT '[]'"),
            ("http_body_type", "VARCHAR(32) DEFAULT 'none'"),
            ("http_body", "TEXT"),
            ("auth_type", "VARCHAR(32) DEFAULT 'none'"),
            ("auth_config", "TEXT DEFAULT '{}'"),
        ]
        for col_name, col_def in api_columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE api_probes ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except Exception:
                pass
                
    # 自动执行单层平铺向四层拓扑结构平滑数据迁移
    migrate_flat_to_hierarchical()


def migrate_flat_to_hierarchical():
    """将老版本 monitor_targets 单层平铺数据无缝迁移为 4 层拓扑资产模型"""
    from app.models import (
        Environment, ServiceGroup, MachineNode, ApiProbe, MonitorTarget
    )
    with Session(engine) as session:
        # 如果新体系中已有环境定义，则不重复初始化
        existing_env = session.exec(select(Environment)).first()
        if existing_env:
            return
        
        # 查找老数据
        old_targets = session.exec(select(MonitorTarget)).all()
        if not old_targets:
            # 建立默认空脚手架环境
            prod_env = Environment(name="生产环境", description="核心线上生产集群", order_num=1)
            session.add(prod_env)
            session.commit()
            session.refresh(prod_env)
            default_grp = ServiceGroup(environment_id=prod_env.id, name="业务服务集群", description="默认业务分组")
            session.add(default_grp)
            session.commit()
            return
        
        # 按照 group_name 归类环境与服务
        env_map = {}       # name -> Environment
        grp_map = {}       # env_id -> ServiceGroup
        machine_map = {}   # (grp_id, host, port) -> MachineNode
        
        for t in old_targets:
            env_name = t.group_name or "生产环境"
            if env_name not in env_map:
                env = session.exec(select(Environment).where(Environment.name == env_name)).first()
                if not env:
                    env = Environment(name=env_name, description=f"{env_name}资产集群")
                    session.add(env)
                    session.commit()
                    session.refresh(env)
                env_map[env_name] = env
                
                # 创建默认分组
                grp = ServiceGroup(environment_id=env.id, name=f"{env_name}核心集群", description="主业务集群")
                session.add(grp)
                session.commit()
                session.refresh(grp)
                grp_map[env.id] = grp
            else:
                env = env_map[env_name]
                grp = grp_map[env.id]
                
            # 机器节点归一化 (host, port)
            m_key = (grp.id, t.host, t.port)
            if m_key not in machine_map:
                machine = MachineNode(
                    group_id=grp.id,
                    name=f"node-{t.host}:{t.port}",
                    host=t.host,
                    port=t.port,
                    cron_interval_minutes=t.cron_interval_minutes,
                    is_active=t.is_active,
                    current_status="ONLINE" if t.current_status == "HEALTHY" else ("OFFLINE" if t.current_status == "DOWN" else "UNKNOWN"),
                    consecutive_failures=t.consecutive_failures,
                    last_tcp_latency_ms=t.last_tcp_latency_ms,
                    last_probed_at=t.last_probed_at,
                    email_receivers=t.email_receivers or []
                )
                session.add(machine)
                session.commit()
                session.refresh(machine)
                machine_map[m_key] = machine
            else:
                machine = machine_map[m_key]
                
            # 创建接口探针
            probe = ApiProbe(
                machine_id=machine.id,
                name=t.name,
                http_path=t.http_path,
                http_method=t.http_method,
                http_headers=t.http_headers or {},
                expected_schema=t.expected_schema,
                cron_interval_minutes=t.cron_interval_minutes,
                is_active=t.is_active,
                current_status=t.current_status,
                consecutive_failures=t.consecutive_failures,
                last_http_code=200 if t.current_status == "HEALTHY" else None,
                last_http_latency_ms=t.last_http_latency_ms,
                last_schema_matched=True if t.current_status == "HEALTHY" else False,
                last_probed_at=t.last_probed_at,
                email_receivers=t.email_receivers or []
            )
            session.add(probe)
        session.commit()
        print(f"[Migration] 成功平滑迁移 {len(old_targets)} 条老版平铺监控数据为四层拓扑结构！")


def get_session():
    """获取数据库会话"""
    with Session(engine) as session:
        yield session
