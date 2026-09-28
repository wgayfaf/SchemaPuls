"""DB Fixture 插件: PostgreSQL 元数据探查器 (Table Schema Inspector)"""
import time
from typing import Dict, Any, List, Optional
import asyncpg

from app.plugins.db_fixture.models import MachineDatabase, TestDbConnectionPayload
from app.plugins.db_fixture.pool_manager import db_pool_manager, _get_ssl_param


async def test_db_connection(payload: TestDbConnectionPayload) -> Dict[str, Any]:
    """测试数据库连通性并获取版本号与网络延迟"""
    start = time.perf_counter()
    ssl_param = _get_ssl_param(payload.ssl_mode)
    conn = await asyncpg.connect(
        host=payload.host,
        port=payload.port,
        database=payload.database,
        user=payload.username,
        password=payload.password or "",
        ssl=ssl_param,
        timeout=float(payload.connect_timeout or 5)
    )
    try:
        version = await conn.fetchval("SELECT version();")
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "ok": True,
            "version": version,
            "latency_ms": latency_ms,
            "message": f"连接成功！延迟 {latency_ms} ms"
        }
    finally:
        await conn.close()


async def list_database_tables(db: MachineDatabase) -> List[str]:
    """读取指定数据库 public schema 下所有物理数据表清单"""
    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """
    async with db_pool_manager.acquire_connection(db) as conn:
        rows = await conn.fetch(query)
        return [r["table_name"] for r in rows]


async def inspect_table_schema(db: MachineDatabase, table_name: str) -> Dict[str, Any]:
    """读取数据表的详细字段结构、数据类型、主键约束及默认值"""
    # 1. 查询主键列
    pk_query = """
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
          AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = 'public'
          AND tc.table_name = $1
        ORDER BY kcu.ordinal_position;
    """
    # 2. 查询字段清单及属性
    cols_query = """
        SELECT
            c.column_name,
            c.data_type,
            c.udt_name,
            c.is_nullable,
            c.column_default,
            c.character_maximum_length,
            c.numeric_precision,
            c.numeric_scale
        FROM information_schema.columns c
        WHERE c.table_schema = 'public'
          AND c.table_name = $1
        ORDER BY c.ordinal_position;
    """

    async with db_pool_manager.acquire_connection(db) as conn:
        pk_rows = await conn.fetch(pk_query, table_name)
        pk_cols = [r["column_name"] for r in pk_rows]

        cols_rows = await conn.fetch(cols_query, table_name)
        columns = []
        for r in cols_rows:
            col_name = r["column_name"]
            is_pk = col_name in pk_cols
            columns.append({
                "column_name": col_name,
                "data_type": r["data_type"],
                "udt_name": r["udt_name"],
                "is_nullable": r["is_nullable"] == "YES",
                "has_default": bool(r["column_default"]),
                "column_default": r["column_default"],
                "is_primary_key": is_pk,
                "max_length": r["character_maximum_length"],
                "numeric_precision": r["numeric_precision"],
                "numeric_scale": r["numeric_scale"]
            })

        return {
            "table_name": table_name,
            "primary_keys": pk_cols,
            "primary_key_column": pk_cols[0] if pk_cols else None,
            "columns": columns
        }
