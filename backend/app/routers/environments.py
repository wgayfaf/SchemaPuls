"""环境层 CRUD 与环境变量池维护"""
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    Environment, ServiceGroup, MachineNode, ApiProbe,
    MonitorTarget,
)
from app.schemas.environment import EnvironmentVariablesPayload
from app.services.scheduler import (
    remove_machine_job, remove_api_job, remove_target_job,
)

router = APIRouter(prefix="/api/environments", tags=["environments"])


@router.get("", response_model=List[Environment])
def list_environments(session: Session = Depends(get_session)):
    return session.exec(select(Environment).order_by(Environment.order_num)).all()


@router.post("", response_model=Environment)
def create_environment(env: Environment, session: Session = Depends(get_session)):
    existing = session.exec(select(Environment).where(Environment.name == env.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"环境 [{env.name}] 已存在")
    session.add(env)
    session.commit()
    session.refresh(env)
    return env


@router.put("/{id}", response_model=Environment)
def update_environment(id: int, data: Environment, session: Session = Depends(get_session)):
    env = session.get(Environment, id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    old_name = env.name
    # 检查是否重名冲突
    if data.name != old_name:
        existing = session.exec(select(Environment).where(Environment.name == data.name)).first()
        if existing and existing.id != id:
            raise HTTPException(status_code=400, detail=f"环境名称 [{data.name}] 已被使用")
        # 联动更新 MonitorTarget 下的 group_name
        targets = session.exec(select(MonitorTarget).where(MonitorTarget.group_name == old_name)).all()
        for t in targets:
            t.group_name = data.name
            session.add(t)
    env.name = data.name
    env.description = data.description
    env.base_url = data.base_url
    env.order_num = data.order_num
    session.add(env)
    session.commit()
    session.refresh(env)
    return env


@router.delete("/{id}")
def delete_environment(id: int, session: Session = Depends(get_session)):
    env = session.get(Environment, id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    # 级联删除关联的 MonitorTarget
    targets = session.exec(select(MonitorTarget).where(MonitorTarget.group_name == env.name)).all()
    for t in targets:
        remove_target_job(t.id)
        session.delete(t)
    # 级联删除分组、机器、探针
    groups = session.exec(select(ServiceGroup).where(ServiceGroup.environment_id == id)).all()
    for g in groups:
        machines = session.exec(select(MachineNode).where(MachineNode.group_id == g.id)).all()
        for m in machines:
            remove_machine_job(m.id)
            apis = session.exec(select(ApiProbe).where(ApiProbe.machine_id == m.id)).all()
            for a in apis:
                remove_api_job(a.id)
                session.delete(a)
            session.delete(m)
        session.delete(g)
    session.delete(env)
    session.commit()
    return {"status": "ok", "message": f"环境 id={id} [{env.name}] 及其下属资产已删除"}


@router.get("/{id}/variables")
def get_environment_variables(id: int, session: Session = Depends(get_session)):
    """获取指定运行环境的环境变量池"""
    env = session.get(Environment, id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    return {
        "environment_id": env.id,
        "environment_name": env.name,
        "variables": env.variables or {}
    }


@router.put("/{id}/variables")
def update_environment_variables(id: int, data: EnvironmentVariablesPayload, session: Session = Depends(get_session)):
    """更新指定运行环境的环境变量池"""
    env = session.get(Environment, id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    env.variables = dict(data.variables or {})
    session.add(env)
    session.commit()
    session.refresh(env)
    return {
        "status": "ok",
        "environment_id": env.id,
        "environment_name": env.name,
        "variables": env.variables
    }



