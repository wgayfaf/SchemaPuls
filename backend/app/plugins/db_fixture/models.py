from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlmodel import SQLModel, Field, JSON, Column
from pydantic import BaseModel


def utc_now() -> datetime:
    """返回带有时区信息的当前时间"""
    return datetime.now(timezone.utc)


class MachineDatabase(SQLModel, table=True):
    """机器归属的目标数据库配置 (支持 PostgreSQL / pg 连通与连接池管控)"""
    __tablename__ = "machine_databases"

    id: Optional[int] = Field(default=None, primary_key=True)
    machine_id: int = Field(index=True)
    name: str = Field(max_length=64, index=True)          # 如 "用户中心PG主库"
    db_type: str = Field(default="postgresql", max_length=32) # 当前聚焦 postgresql
    host: str = Field(max_length=255)
    port: int = Field(default=5432)
    database: str = Field(max_length=128)
    username: str = Field(max_length=128)
    password: str = Field(default="", max_length=255)
    ssl_mode: str = Field(default="prefer", max_length=32) # disable, prefer, require
    pool_size: int = Field(default=10)                    # 最大连接池上限，防止连接数爆炸
    connect_timeout: int = Field(default=10)              # 连接超时(秒)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MachineDatabasePayload(BaseModel):
    """机器数据库配置创建/更新载荷"""
    machine_id: int
    name: str
    db_type: str = "postgresql"
    host: str
    port: int = 5432
    database: str
    username: str
    password: str = ""
    ssl_mode: str = "prefer"
    pool_size: int = 10
    connect_timeout: int = 10


class TestDbConnectionPayload(BaseModel):
    """测试数据库连通性载荷"""
    host: str
    port: int = 5432
    database: str
    username: str
    password: str = ""
    ssl_mode: str = "prefer"
    connect_timeout: int = 10


class GenerateMockDataPayload(BaseModel):
    """生成测试数据载荷"""
    table_name: str
    columns: Optional[List[Dict[str, Any]]] = None
