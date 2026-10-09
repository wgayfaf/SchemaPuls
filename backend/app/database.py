from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy import text
import os

DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 支持通过环境变量指定数据库位置 (如 Docker 卷挂载), 默认沿用 backend/monitor.db
DB_PATH = os.environ.get("SCHEMAPULSE_DB") or os.path.join(DB_DIR, "monitor.db")
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
        MonitorTarget, ProbeHistory, SmtpConfig,
        ScenarioProbe, ScenarioProbeHistory,
        MachineDatabase
    )
    # 创建所有四层模型新表以及兼容表
    # 兼容迁移: 老版本场景历史表 (success/failed_step/steps_result 结构, 旧引擎未上线无业务数据) 重建为新结构
    with engine.connect() as conn:
        try:
            cols = [r[1] for r in conn.execute(text("PRAGMA table_info(scenario_probe_histories)")).fetchall()]
            if cols and "is_success" not in cols:
                conn.execute(text("DROP TABLE scenario_probe_histories"))
                conn.commit()
                print("[Migration] 旧版 scenario_probe_histories 表结构已重建为新版拨测引擎结构")
        except Exception:
            pass
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
            ("base_url", "VARCHAR(255)"),
            ("http_params", "TEXT DEFAULT '[]'"),
            ("http_body_type", "VARCHAR(32) DEFAULT 'none'"),
            ("http_body", "TEXT"),
            ("auth_type", "VARCHAR(32) DEFAULT 'none'"),
            ("auth_config", "TEXT DEFAULT '{}'"),
            ("pre_actions", "TEXT DEFAULT '[]'"),
            ("post_actions", "TEXT DEFAULT '[]'"),
            ("db_fixture", "TEXT DEFAULT NULL"),
        ]
        for col_name, col_def in api_columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE api_probes ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except Exception:
                pass  # 若字段已存在则忽略异常

        # api_probe_histories 表新增 db_fixture_summary 列
        try:
            conn.execute(text("ALTER TABLE api_probe_histories ADD COLUMN db_fixture_summary TEXT DEFAULT NULL"))
            conn.commit()
        except Exception:
            pass

        # smtp_config 表新增全局告警收件人列 (兼容已建表的老库)
        try:
            conn.execute(text("ALTER TABLE smtp_config ADD COLUMN alert_receivers TEXT DEFAULT '[]'"))
            conn.commit()
        except Exception:
            pass
        # smtp_config 表新增邮件告警总开关列
        try:
            conn.execute(text("ALTER TABLE smtp_config ADD COLUMN smtp_enabled BOOL DEFAULT 1"))
            conn.commit()
        except Exception:
            pass

        env_columns_to_add = [
            ("base_url", "VARCHAR(255)"),
            ("variables", "TEXT DEFAULT '{}'"),
        ]
        for col_name, col_def in env_columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE environments ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except Exception:
                pass


        machine_columns_to_add = [
            ("base_url", "VARCHAR(255)"),
            ("ping_ok", "BOOLEAN"),
            ("last_ping_latency_ms", "FLOAT"),
            ("tcp_ok", "BOOLEAN"),
            ("last_error_message", "TEXT"),
        ]
        for col_name, col_def in machine_columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE machine_nodes ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except Exception:
                pass

        history_columns_to_add = [
            ("ping_ok", "BOOLEAN DEFAULT 0"),
            ("ping_latency_ms", "FLOAT"),
        ]
        for col_name, col_def in history_columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE machine_probe_histories ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except Exception:
                pass

        api_history_columns_to_add = [
            ("assertions_result", "TEXT DEFAULT '[]'"),
        ]
        for col_name, col_def in api_history_columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE api_probe_histories ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except Exception:
                pass

        scenario_columns_to_add = [
            ("last_schema_matched", "BOOLEAN"),
            ("variables", "TEXT DEFAULT '{}'"),
        ]
        for col_name, col_def in scenario_columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE scenario_probes ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except Exception:
                pass

        scenario_history_columns_to_add = [
            ("scenario_variables", "TEXT DEFAULT '{}'"),
        ]
        for col_name, col_def in scenario_history_columns_to_add:
            try:
                conn.execute(text(f"ALTER TABLE scenario_probe_histories ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except Exception:
                pass

        # 自动清理已删除接口/机器残留的孤儿历史与幽灵老目标，保证系统数据源 100% 严格一致
        try:
            conn.execute(text("DELETE FROM api_probe_histories WHERE api_probe_id NOT IN (SELECT id FROM api_probes)"))
            conn.execute(text("DELETE FROM machine_probe_histories WHERE machine_id NOT IN (SELECT id FROM machine_nodes)"))
            conn.execute(text("DELETE FROM scenario_probe_histories WHERE scenario_id NOT IN (SELECT id FROM scenario_probes)"))
            conn.execute(text("DELETE FROM monitor_targets WHERE name NOT IN (SELECT name FROM api_probes)"))
            conn.execute(text("DELETE FROM probe_histories WHERE target_id NOT IN (SELECT id FROM monitor_targets)"))
            conn.commit()
        except Exception:
            pass

    # 自动执行单层平铺向四层拓扑结构平滑数据迁移
    migrate_flat_to_hierarchical()


def migrate_flat_to_hierarchical():
    """将老版本 monitor_targets 单层平铺数据无缝迁移为 4 层拓扑资产模型"""
    from datetime import datetime, timezone
    from app.models import (
        Environment, ServiceGroup, MachineNode, ApiProbe, MonitorTarget
    )

    def _ensure_utc(dt):
        if dt is None:
            return None
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except Exception:
                return datetime.now(timezone.utc)
        if getattr(dt, "tzinfo", None) is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

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
                    last_probed_at=_ensure_utc(t.last_probed_at),
                    last_alert_at=_ensure_utc(t.last_alert_at),
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
                last_probed_at=_ensure_utc(t.last_probed_at),
                last_alert_at=_ensure_utc(t.last_alert_at),
                email_receivers=t.email_receivers or []
            )
            session.add(probe)
        session.commit()
        print(f"[Migration] 成功平滑迁移 {len(old_targets)} 条老版平铺监控数据为四层拓扑结构！")


def get_session():
    """获取数据库会话"""
    with Session(engine) as session:
        yield session
