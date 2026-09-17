"""机器节点层 CRUD、即时连通性探测、接口批量克隆与时序指标"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select, func
from sqlalchemy import text

from app.database import get_session
from app.models import (
    Environment, ServiceGroup, MachineNode, ApiProbe,
    MachineProbeHistory,
)
from app.schemas.machine import MachinePayload, CloneApisRequest
from app.services.probe_service import execute_machine_probe
from app.services.scheduler import add_machine_job, remove_machine_job, add_api_job, remove_api_job

router = APIRouter(prefix="/api/machines", tags=["machines"])


@router.get("")
def list_machines(environment_id: Optional[int] = None, group_id: Optional[int] = None, session: Session = Depends(get_session)):
    stmt = select(MachineNode)
    if group_id:
        stmt = stmt.where(MachineNode.group_id == group_id)
    machines = session.exec(stmt).all()

    result = []
    for m in machines:
        grp = session.get(ServiceGroup, m.group_id) if m.group_id else None
        env = session.get(Environment, grp.environment_id) if grp else None

        # 过滤环境
        if environment_id and (not env or env.id != environment_id):
            continue

        api_count = session.exec(select(func.count(ApiProbe.id)).where(ApiProbe.machine_id == m.id)).one() or 0

        m_dict = {
            "id": m.id,
            "name": m.name,
            "host": m.host,
            "port": m.port,
            "base_url": m.base_url,
            "cron_interval_minutes": m.cron_interval_minutes,
            "is_active": m.is_active,
            "retry_threshold": m.retry_threshold,
            "silence_minutes": m.silence_minutes,
            "email_receivers": m.email_receivers or [],
            "current_status": m.current_status,
            "consecutive_failures": m.consecutive_failures,
            "ping_ok": m.ping_ok,
            "last_ping_latency_ms": m.last_ping_latency_ms,
            "tcp_ok": m.tcp_ok,
            "last_tcp_latency_ms": m.last_tcp_latency_ms,
            "last_error_message": m.last_error_message,
            "last_probed_at": m.last_probed_at.isoformat() if m.last_probed_at else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "group_id": m.group_id,
            "group_name": grp.name if grp else "核心集群",
            "environment_id": env.id if env else None,
            "environment_name": env.name if env else "默认环境",
            "api_count": api_count
        }
        result.append(m_dict)
    return result


@router.post("")
def create_machine(data: MachinePayload, session: Session = Depends(get_session)):
    group_id = data.group_id
    if not group_id:
        if data.environment_id:
            env = session.get(Environment, data.environment_id)
            if not env:
                raise HTTPException(status_code=404, detail="Associated Environment not found")
            grp = session.exec(select(ServiceGroup).where(ServiceGroup.environment_id == env.id)).first()
            if not grp:
                grp = ServiceGroup(environment_id=env.id, name=f"{env.name}核心集群", description="默认业务集群")
                session.add(grp)
                session.commit()
                session.refresh(grp)
            group_id = grp.id
        else:
            first_grp = session.exec(select(ServiceGroup)).first()
            if not first_grp:
                env = Environment(name="生产环境", description="核心线上生产集群", order_num=1)
                session.add(env)
                session.commit()
                session.refresh(env)
                first_grp = ServiceGroup(environment_id=env.id, name="生产环境核心集群", description="主业务集群")
                session.add(first_grp)
                session.commit()
                session.refresh(first_grp)
            group_id = first_grp.id

    machine = MachineNode(
        group_id=group_id,
        name=data.name,
        host=data.host,
        port=data.port,
        base_url=data.base_url.strip() if data.base_url and data.base_url.strip() else None,
        cron_interval_minutes=data.cron_interval_minutes,
        is_active=data.is_active,
        retry_threshold=data.retry_threshold,
        silence_minutes=data.silence_minutes,
        email_receivers=data.email_receivers
    )
    session.add(machine)
    session.commit()
    session.refresh(machine)
    add_machine_job(machine)

    grp = session.get(ServiceGroup, machine.group_id)
    env = session.get(Environment, grp.environment_id) if grp else None

    return {
        "id": machine.id,
        "name": machine.name,
        "host": machine.host,
        "port": machine.port,
        "base_url": machine.base_url,
        "cron_interval_minutes": machine.cron_interval_minutes,
        "is_active": machine.is_active,
        "current_status": machine.current_status,
        "ping_ok": machine.ping_ok,
        "last_ping_latency_ms": machine.last_ping_latency_ms,
        "tcp_ok": machine.tcp_ok,
        "last_tcp_latency_ms": machine.last_tcp_latency_ms,
        "last_error_message": machine.last_error_message,
        "email_receivers": machine.email_receivers or [],
        "group_id": machine.group_id,
        "group_name": grp.name if grp else "核心集群",
        "environment_id": env.id if env else None,
        "environment_name": env.name if env else "默认环境",
        "api_count": 0
    }


@router.put("/{id}")
def update_machine(id: int, data: MachinePayload, session: Session = Depends(get_session)):
    machine = session.get(MachineNode, id)
    if not machine:
        raise HTTPException(status_code=404, detail="MachineNode not found")

    if data.environment_id:
        env = session.get(Environment, data.environment_id)
        if env:
            grp = session.exec(select(ServiceGroup).where(ServiceGroup.environment_id == env.id)).first()
            if not grp:
                grp = ServiceGroup(environment_id=env.id, name=f"{env.name}核心集群", description="默认业务集群")
                session.add(grp)
                session.commit()
                session.refresh(grp)
            machine.group_id = grp.id
    elif data.group_id:
        machine.group_id = data.group_id

    machine.name = data.name
    machine.host = data.host
    machine.port = data.port
    machine.base_url = data.base_url.strip() if data.base_url and data.base_url.strip() else None
    machine.cron_interval_minutes = data.cron_interval_minutes
    machine.is_active = data.is_active
    machine.email_receivers = data.email_receivers
    session.add(machine)
    session.commit()
    session.refresh(machine)
    add_machine_job(machine)

    grp = session.get(ServiceGroup, machine.group_id)
    env = session.get(Environment, grp.environment_id) if grp else None

    return {
        "id": machine.id,
        "name": machine.name,
        "host": machine.host,
        "port": machine.port,
        "base_url": machine.base_url,
        "cron_interval_minutes": machine.cron_interval_minutes,
        "is_active": machine.is_active,
        "current_status": machine.current_status,
        "ping_ok": machine.ping_ok,
        "last_ping_latency_ms": machine.last_ping_latency_ms,
        "tcp_ok": machine.tcp_ok,
        "last_tcp_latency_ms": machine.last_tcp_latency_ms,
        "last_error_message": machine.last_error_message,
        "email_receivers": machine.email_receivers or [],
        "group_id": machine.group_id,
        "group_name": grp.name if grp else "核心集群",
        "environment_id": env.id if env else None,
        "environment_name": env.name if env else "默认环境"
    }


@router.delete("/{id}")
def delete_machine(id: int, session: Session = Depends(get_session)):
    machine = session.get(MachineNode, id)
    if not machine:
        raise HTTPException(status_code=404, detail="MachineNode not found")
    remove_machine_job(id)
    apis = session.exec(select(ApiProbe).where(ApiProbe.machine_id == id)).all()
    for a in apis:
        remove_api_job(a.id)
        session.exec(text(f"DELETE FROM api_probe_histories WHERE api_probe_id = {a.id}"))
        session.delete(a)
    session.exec(text(f"DELETE FROM machine_probe_histories WHERE machine_id = {id}"))
    session.delete(machine)
    session.commit()
    return {"status": "ok", "message": f"机器节点 id={id} 已删除"}


@router.post("/{id}/trigger")
async def trigger_machine_probe(id: int):
    """手动立即触发对指定机器节点的端口连通性探测"""
    try:
        history = await execute_machine_probe(id)
        return history
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{machine_id}/environment")
def get_machine_environment(machine_id: int, session: Session = Depends(get_session)):
    """根据机器节点获取其归属的运行环境及当前环境变量池"""
    machine = session.get(MachineNode, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="MachineNode not found")
    grp = session.get(ServiceGroup, machine.group_id) if machine.group_id else None
    env = session.get(Environment, grp.environment_id) if grp and grp.environment_id else None
    return {
        "machine_id": machine.id,
        "machine_name": machine.name,
        "group_id": grp.id if grp else None,
        "group_name": grp.name if grp else None,
        "environment_id": env.id if env else None,
        "environment_name": env.name if env else "默认环境",
        "environment_description": env.description if env else "",
        "environment_base_url": env.base_url if env else None,
        "variables": env.variables or {} if env else {}
    }


@router.post("/{source_machine_id}/clone-apis")
def clone_machine_apis(
    source_machine_id: int,
    req: CloneApisRequest,
    session: Session = Depends(get_session)
):
    """将源机器名下的所有接口探针定义批量同步克隆到指定的其他机器节点"""
    source_machine = session.get(MachineNode, source_machine_id)
    if not source_machine:
        raise HTTPException(status_code=404, detail=f"Source MachineNode {source_machine_id} not found")

    source_apis = session.exec(select(ApiProbe).where(ApiProbe.machine_id == source_machine_id)).all()
    if not source_apis:
        return {"status": "ok", "cloned_count": 0, "message": "源机器未配置任何接口探针"}

    cloned_total = 0
    for t_id in req.target_machine_ids:
        if t_id == source_machine_id:
            continue
        target_machine = session.get(MachineNode, t_id)
        if not target_machine:
            continue

        existing_apis = session.exec(select(ApiProbe).where(ApiProbe.machine_id == t_id)).all()
        existing_paths = {a.http_path: a for a in existing_apis}

        for s_api in source_apis:
            if s_api.http_path in existing_paths:
                if req.override_existing:
                    # 覆盖更新已有探针规则
                    ex_api = existing_paths[s_api.http_path]
                    ex_api.name = s_api.name
                    ex_api.http_method = s_api.http_method
                    ex_api.http_headers = dict(s_api.http_headers)
                    ex_api.expected_schema = dict(s_api.expected_schema)
                    ex_api.cron_interval_minutes = s_api.cron_interval_minutes
                    ex_api.is_active = s_api.is_active
                    ex_api.email_receivers = list(s_api.email_receivers)
                    session.add(ex_api)
                    add_api_job(ex_api)
                    cloned_total += 1
            else:
                # 克隆新探针
                new_api = ApiProbe(
                    machine_id=t_id,
                    name=s_api.name,
                    http_path=s_api.http_path,
                    http_method=s_api.http_method,
                    http_headers=dict(s_api.http_headers),
                    expected_schema=dict(s_api.expected_schema),
                    cron_interval_minutes=s_api.cron_interval_minutes,
                    is_active=s_api.is_active,
                    email_receivers=list(s_api.email_receivers)
                )
                session.add(new_api)
                session.commit()
                session.refresh(new_api)
                add_api_job(new_api)
                cloned_total += 1

    session.commit()
    return {
        "status": "ok",
        "cloned_count": cloned_total,
        "message": f"成功将 {len(source_apis)} 个接口定义同步至 {len(req.target_machine_ids)} 台机器，产生 {cloned_total} 次探针生效！"
    }


@router.get("/{id}/metrics")
def get_machine_metrics(id: int, session: Session = Depends(get_session)):
    records = session.exec(
        select(MachineProbeHistory)
        .where(MachineProbeHistory.machine_id == id)
        .order_by(MachineProbeHistory.probed_at.desc())
        .limit(100)
    ).all()
    points = [
        {
            "time": r.probed_at.strftime("%H:%M:%S"),
            "tcp_ms": r.tcp_latency_ms or 0.0,
            "tcp_ok": r.tcp_ok
        }
        for r in reversed(records)
    ]
    return {"machine_id": id, "points": points}
