"""DB Fixture 插件: 数据库管理与 Schema 探查 REST 路由"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models import MachineNode
from app.plugins.db_fixture.models import (
    MachineDatabase,
    MachineDatabasePayload,
    TestDbConnectionPayload,
    GenerateMockDataPayload
)
from app.plugins.db_fixture.pool_manager import db_pool_manager
from app.plugins.db_fixture.inspector import (
    test_db_connection,
    list_database_tables,
    inspect_table_schema
)
from app.plugins.db_fixture.generator import (
    generate_mock_data_for_table
)

router = APIRouter(prefix="/api/machine-databases", tags=["machine-databases"])


@router.get("", response_model=List[MachineDatabase])
def list_databases(
    machine_id: Optional[int] = Query(None, description="按机器节点筛选"),
    session: Session = Depends(get_session)
):
    """获取数据库配置列表"""
    stmt = select(MachineDatabase)
    if machine_id:
        stmt = stmt.where(MachineDatabase.machine_id == machine_id)
    return session.exec(stmt).all()


@router.post("", response_model=MachineDatabase)
def create_database(
    data: MachineDatabasePayload,
    session: Session = Depends(get_session)
):
    """创建机器归属的数据库连接配置"""
    machine = session.get(MachineNode, data.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="关联机器节点不存在")

    db = MachineDatabase(
        machine_id=data.machine_id,
        name=data.name.strip(),
        db_type=data.db_type or "postgresql",
        host=data.host.strip(),
        port=data.port or 5432,
        database=data.database.strip(),
        username=data.username.strip(),
        password=data.password or "",
        ssl_mode=data.ssl_mode or "prefer",
        pool_size=data.pool_size or 10,
        connect_timeout=data.connect_timeout or 10
    )
    session.add(db)
    session.commit()
    session.refresh(db)
    return db


@router.put("/{id}", response_model=MachineDatabase)
async def update_database(
    id: int,
    data: MachineDatabasePayload,
    session: Session = Depends(get_session)
):
    """更新数据库配置并自动失效旧连接池"""
    db = session.get(MachineDatabase, id)
    if not db:
        raise HTTPException(status_code=404, detail="数据库配置不存在")

    db.name = data.name.strip()
    db.db_type = data.db_type or "postgresql"
    db.host = data.host.strip()
    db.port = data.port or 5432
    db.database = data.database.strip()
    db.username = data.username.strip()
    db.password = data.password if data.password is not None else db.password
    db.ssl_mode = data.ssl_mode or "prefer"
    db.pool_size = data.pool_size or 10
    db.connect_timeout = data.connect_timeout or 10
    db.updated_at = datetime.utcnow()

    session.add(db)
    session.commit()
    session.refresh(db)

    # 释放旧连接池，下次请求时自动使用新参数重连
    await db_pool_manager.invalidate_pool(id)
    return db


@router.delete("/{id}")
async def delete_database(
    id: int,
    session: Session = Depends(get_session)
):
    """删除数据库配置并释放连接池"""
    db = session.get(MachineDatabase, id)
    if not db:
        raise HTTPException(status_code=404, detail="数据库配置不存在")

    session.delete(db)
    session.commit()
    await db_pool_manager.invalidate_pool(id)
    return {"ok": True, "message": "数据库配置已删除"}


@router.post("/test-connection")
async def test_connection(data: TestDbConnectionPayload):
    """测试指定 PostgreSQL 数据库连接连通性与耗时"""
    try:
        res = await test_db_connection(data)
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"数据库连通失败: {str(e)}")


@router.get("/{id}/tables")
async def get_tables(
    id: int,
    session: Session = Depends(get_session)
):
    """获取指定数据库下的物理表清单 (public schema)"""
    db = session.get(MachineDatabase, id)
    if not db:
        raise HTTPException(status_code=404, detail="数据库配置不存在")
    try:
        tables = await list_database_tables(db)
        return {"database_id": id, "tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表清单失败: {str(e)}")


@router.get("/{id}/table-schema")
async def get_table_schema(
    id: int,
    table_name: str = Query(..., description="数据表名称"),
    session: Session = Depends(get_session)
):
    """获取指定数据表的字段定义、数据类型与主键属性"""
    db = session.get(MachineDatabase, id)
    if not db:
        raise HTTPException(status_code=404, detail="数据库配置不存在")
    try:
        schema = await inspect_table_schema(db, table_name)
        return schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"探查数据表结构失败: {str(e)}")


@router.post("/{id}/generate-mock-data")
async def generate_mock_data(
    id: int,
    payload: GenerateMockDataPayload,
    session: Session = Depends(get_session)
):
    """基于表结构元数据自动推导并生成一套 Mock 测试数据及注入变量建议"""
    db = session.get(MachineDatabase, id)
    if not db:
        raise HTTPException(status_code=404, detail="数据库配置不存在")

    try:
        schema = await inspect_table_schema(db, payload.table_name)
        mock_data = generate_mock_data_for_table(schema)
        return mock_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"智能生成测试数据失败: {str(e)}")
