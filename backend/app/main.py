from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, func
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from genson import SchemaBuilder
from fastapi.responses import RedirectResponse
import os

from app.database import init_db, get_session
from app.models import (
    Environment, ServiceGroup, MachineNode, ApiProbe,
    MachineProbeHistory, ApiProbeHistory,
    MonitorTarget, ProbeHistory
)
from app.services.probe_service import (
    execute_machine_probe,
    execute_api_probe,
    execute_probe_for_target,
    check_schema
)
from app.services.scheduler import (
    init_scheduler,
    add_machine_job, remove_machine_job,
    add_api_job, remove_api_job,
    add_target_job, remove_target_job,
    scheduler
)
from app.services.metric_service import get_dashboard_summary, get_target_metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_scheduler()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="SchemaPulse API",
    description="服务监控资产层级化与解耦探测系统 (前后端分离架构)",
    version="2.0.0",
    lifespan=lifespan
)

# 允许全域跨域 (CORS)，全面支持独立前端工程 (http://127.0.0.1:3000、http://localhost:3000 等)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    """纯后端 API 根路径：返回服务运行元数据及前端服务指引"""
    return {
        "name": "SchemaPulse API Server",
        "version": "2.0.0",
        "status": "online",
        "architecture": "Decoupled (Frontend & Backend Separated)",
        "frontend_dev_url": "http://127.0.0.1:3000",
        "api_docs_url": "/docs",
        "redoc_url": "/redoc"
    }


@app.get("/web")
@app.get("/dashboard")
def get_web_console():
    """向后兼容路由：重定向至独立前端服务"""
    return RedirectResponse(url="http://127.0.0.1:3000")


# ==========================================================
# 一、 树状拓扑聚合接口 (供前端一次性拉取整棵拓扑树)
# ==========================================================

@app.get("/api/topology/tree")
def get_topology_tree(session: Session = Depends(get_session)):
    """获取完整的四层拓扑结构: 环境 -> 分组 -> 机器节点 -> 接口探针"""
    environments = session.exec(select(Environment).order_by(Environment.order_num)).all()
    result = []
    for env in environments:
        env_dict = {
            "id": env.id,
            "name": env.name,
            "description": env.description,
            "order_num": env.order_num,
            "groups": []
        }
        groups = session.exec(select(ServiceGroup).where(ServiceGroup.environment_id == env.id)).all()
        for grp in groups:
            grp_dict = {
                "id": grp.id,
                "name": grp.name,
                "description": grp.description,
                "machines": []
            }
            machines = session.exec(select(MachineNode).where(MachineNode.group_id == grp.id)).all()
            for m in machines:
                m_dict = {
                    "id": m.id,
                    "name": m.name,
                    "host": m.host,
                    "port": m.port,
                    "cron_interval_minutes": m.cron_interval_minutes,
                    "is_active": m.is_active,
                    "current_status": m.current_status,
                    "consecutive_failures": m.consecutive_failures,
                    "last_tcp_latency_ms": m.last_tcp_latency_ms,
                    "last_probed_at": m.last_probed_at.isoformat() if m.last_probed_at else None,
                    "apis": []
                }
                apis = session.exec(select(ApiProbe).where(ApiProbe.machine_id == m.id)).all()
                for a in apis:
                    a_dict = {
                        "id": a.id,
                        "name": a.name,
                        "http_path": a.http_path,
                        "http_method": a.http_method,
                        "expected_schema": a.expected_schema,
                        "cron_interval_minutes": a.cron_interval_minutes,
                        "is_active": a.is_active,
                        "current_status": a.current_status,
                        "consecutive_failures": a.consecutive_failures,
                        "last_http_code": a.last_http_code,
                        "last_http_latency_ms": a.last_http_latency_ms,
                        "last_schema_matched": a.last_schema_matched,
                        "last_probed_at": a.last_probed_at.isoformat() if a.last_probed_at else None
                    }
                    m_dict["apis"].append(a_dict)
                grp_dict["machines"].append(m_dict)
            env_dict["groups"].append(grp_dict)
        result.append(env_dict)
    return result


# ==========================================================
# 二、 分层独立维护 CRUD
# ==========================================================

# 1. 环境层 CRUD
@app.get("/api/environments", response_model=List[Environment])
def list_environments(session: Session = Depends(get_session)):
    return session.exec(select(Environment).order_by(Environment.order_num)).all()


@app.post("/api/environments", response_model=Environment)
def create_environment(env: Environment, session: Session = Depends(get_session)):
    existing = session.exec(select(Environment).where(Environment.name == env.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"环境 [{env.name}] 已存在")
    session.add(env)
    session.commit()
    session.refresh(env)
    return env


@app.put("/api/environments/{id}", response_model=Environment)
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
    env.order_num = data.order_num
    session.add(env)
    session.commit()
    session.refresh(env)
    return env


@app.delete("/api/environments/{id}")
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


# 2. 分组层 CRUD
@app.get("/api/groups", response_model=List[ServiceGroup])
def list_service_groups(environment_id: Optional[int] = None, session: Session = Depends(get_session)):
    stmt = select(ServiceGroup)
    if environment_id:
        stmt = stmt.where(ServiceGroup.environment_id == environment_id)
    return session.exec(stmt).all()


@app.post("/api/groups", response_model=ServiceGroup)
def create_service_group(group: ServiceGroup, session: Session = Depends(get_session)):
    env = session.get(Environment, group.environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Associated Environment not found")
    session.add(group)
    session.commit()
    session.refresh(group)
    return group


@app.put("/api/groups/{id}", response_model=ServiceGroup)
def update_service_group(id: int, data: ServiceGroup, session: Session = Depends(get_session)):
    grp = session.get(ServiceGroup, id)
    if not grp:
        raise HTTPException(status_code=404, detail="ServiceGroup not found")
    grp.name = data.name
    grp.description = data.description
    session.add(grp)
    session.commit()
    session.refresh(grp)
    return grp


@app.delete("/api/groups/{id}")
def delete_service_group(id: int, session: Session = Depends(get_session)):
    grp = session.get(ServiceGroup, id)
    if not grp:
        raise HTTPException(status_code=404, detail="ServiceGroup not found")
    machines = session.exec(select(MachineNode).where(MachineNode.group_id == id)).all()
    for m in machines:
        remove_machine_job(m.id)
        apis = session.exec(select(ApiProbe).where(ApiProbe.machine_id == m.id)).all()
        for a in apis:
            remove_api_job(a.id)
            session.delete(a)
        session.delete(m)
    session.delete(grp)
    session.commit()
    return {"status": "ok", "message": f"分组 id={id} 及其下属资产已删除"}


class MachinePayload(BaseModel):
    name: str
    host: str
    port: int
    environment_id: Optional[int] = None
    group_id: Optional[int] = None
    cron_interval_minutes: int = 5
    is_active: bool = True
    email_receivers: List[str] = []
    retry_threshold: int = 3
    silence_minutes: int = 30


# 3. 机器节点层 CRUD 与即时连通性探测
@app.get("/api/machines")
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
            
        target_count = session.exec(select(func.count(MonitorTarget.id)).where(MonitorTarget.host == m.host, MonitorTarget.port == m.port)).one() or 0
        api_count = session.exec(select(func.count(ApiProbe.id)).where(ApiProbe.machine_id == m.id)).one() or 0
        
        m_dict = {
            "id": m.id,
            "name": m.name,
            "host": m.host,
            "port": m.port,
            "cron_interval_minutes": m.cron_interval_minutes,
            "is_active": m.is_active,
            "retry_threshold": m.retry_threshold,
            "silence_minutes": m.silence_minutes,
            "email_receivers": m.email_receivers or [],
            "current_status": m.current_status,
            "consecutive_failures": m.consecutive_failures,
            "last_tcp_latency_ms": m.last_tcp_latency_ms,
            "last_probed_at": m.last_probed_at.isoformat() if m.last_probed_at else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "group_id": m.group_id,
            "group_name": grp.name if grp else "核心集群",
            "environment_id": env.id if env else None,
            "environment_name": env.name if env else "默认环境",
            "api_count": max(target_count, api_count)
        }
        result.append(m_dict)
    return result


@app.post("/api/machines")
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
        "cron_interval_minutes": machine.cron_interval_minutes,
        "is_active": machine.is_active,
        "current_status": machine.current_status,
        "last_tcp_latency_ms": machine.last_tcp_latency_ms,
        "email_receivers": machine.email_receivers or [],
        "group_id": machine.group_id,
        "group_name": grp.name if grp else "核心集群",
        "environment_id": env.id if env else None,
        "environment_name": env.name if env else "默认环境",
        "api_count": 0
    }


@app.put("/api/machines/{id}")
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
        "cron_interval_minutes": machine.cron_interval_minutes,
        "is_active": machine.is_active,
        "current_status": machine.current_status,
        "last_tcp_latency_ms": machine.last_tcp_latency_ms,
        "email_receivers": machine.email_receivers or [],
        "group_id": machine.group_id,
        "group_name": grp.name if grp else "核心集群",
        "environment_id": env.id if env else None,
        "environment_name": env.name if env else "默认环境"
    }


@app.delete("/api/machines/{id}")
def delete_machine(id: int, session: Session = Depends(get_session)):
    machine = session.get(MachineNode, id)
    if not machine:
        raise HTTPException(status_code=404, detail="MachineNode not found")
    remove_machine_job(id)
    apis = session.exec(select(ApiProbe).where(ApiProbe.machine_id == id)).all()
    for a in apis:
        remove_api_job(a.id)
        session.delete(a)
    session.delete(machine)
    session.commit()
    return {"status": "ok", "message": f"机器节点 id={id} 已删除"}


@app.post("/api/machines/{id}/trigger")
async def trigger_machine_probe(id: int):
    """手动立即触发对指定机器节点的端口连通性探测"""
    try:
        history = await execute_machine_probe(id)
        return history
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


class ApiPayload(BaseModel):
    machine_id: int
    name: str
    http_path: str = "/health"
    http_method: str = "GET"
    http_headers: Dict[str, str] = {}
    expected_schema: Dict[str, Any]
    cron_interval_minutes: int = 5
    is_active: bool = True
    email_receivers: List[str] = []
    retry_threshold: int = 3
    silence_minutes: int = 30


# 4. 接口探针层 CRUD 与即时业务校验
@app.get("/api/apis")
def list_apis(
    machine_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    stmt = select(ApiProbe)
    if machine_id:
        stmt = stmt.where(ApiProbe.machine_id == machine_id)
    apis = session.exec(stmt).all()
    
    result = []
    for a in apis:
        m = session.get(MachineNode, a.machine_id)
        grp = session.get(ServiceGroup, m.group_id) if m and m.group_id else None
        env = session.get(Environment, grp.environment_id) if grp else None
        
        if environment_id and (not env or env.id != environment_id):
            continue
            
        host = m.host if m else "127.0.0.1"
        port = m.port if m else 80
        scheme = "https" if port == 443 else "http"
        port_str = f":{port}" if port not in [80, 443] else ""
        path = a.http_path if a.http_path.startswith("/") else f"/{a.http_path}"
        full_url = f"{scheme}://{host}{port_str}{path}"
        
        result.append({
            "id": a.id,
            "machine_id": a.machine_id,
            "name": a.name,
            "http_path": a.http_path,
            "http_method": a.http_method,
            "http_headers": a.http_headers or {},
            "expected_schema": a.expected_schema,
            "cron_interval_minutes": a.cron_interval_minutes,
            "is_active": a.is_active,
            "retry_threshold": a.retry_threshold,
            "silence_minutes": a.silence_minutes,
            "email_receivers": a.email_receivers or [],
            "current_status": a.current_status,
            "consecutive_failures": a.consecutive_failures,
            "last_http_code": a.last_http_code,
            "last_http_latency_ms": a.last_http_latency_ms,
            "last_schema_matched": a.last_schema_matched,
            "last_probed_at": a.last_probed_at.isoformat() if a.last_probed_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "machine_name": m.name if m else f"node-{host}:{port}",
            "machine_host": host,
            "machine_port": port,
            "machine_status": m.current_status if m else "UNKNOWN",
            "environment_id": env.id if env else None,
            "environment_name": env.name if env else "默认环境",
            "group_name": grp.name if grp else "核心集群",
            "full_url": full_url
        })
    return result


@app.post("/api/apis")
def create_api(data: ApiPayload, session: Session = Depends(get_session)):
    machine = session.get(MachineNode, data.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Associated MachineNode not found")
        
    api = ApiProbe(
        machine_id=data.machine_id,
        name=data.name,
        http_path=data.http_path,
        http_method=data.http_method,
        http_headers=data.http_headers,
        expected_schema=data.expected_schema,
        cron_interval_minutes=data.cron_interval_minutes,
        is_active=data.is_active,
        retry_threshold=data.retry_threshold,
        silence_minutes=data.silence_minutes,
        email_receivers=data.email_receivers
    )
    session.add(api)
    session.commit()
    session.refresh(api)
    add_api_job(api)
    
    grp = session.get(ServiceGroup, machine.group_id) if machine.group_id else None
    env = session.get(Environment, grp.environment_id) if grp else None
    
    # 同步维护 MonitorTarget 以保障大盘与兼容平铺视图
    target = MonitorTarget(
        name=api.name,
        group_name=env.name if env else "生产环境",
        host=machine.host,
        port=machine.port,
        http_path=api.http_path,
        http_method=api.http_method,
        cron_interval_minutes=api.cron_interval_minutes,
        expected_schema=api.expected_schema,
        email_receivers=api.email_receivers,
        retry_threshold=api.retry_threshold,
        silence_minutes=api.silence_minutes
    )
    session.add(target)
    session.commit()
    session.refresh(target)
    add_target_job(target)
    
    scheme = "https" if machine.port == 443 else "http"
    port_str = f":{machine.port}" if machine.port not in [80, 443] else ""
    path = api.http_path if api.http_path.startswith("/") else f"/{api.http_path}"
    
    return {
        "id": api.id,
        "machine_id": api.machine_id,
        "name": api.name,
        "http_path": api.http_path,
        "http_method": api.http_method,
        "expected_schema": api.expected_schema,
        "cron_interval_minutes": api.cron_interval_minutes,
        "is_active": api.is_active,
        "current_status": api.current_status,
        "machine_name": machine.name,
        "machine_host": machine.host,
        "machine_port": machine.port,
        "environment_id": env.id if env else None,
        "environment_name": env.name if env else "默认环境",
        "full_url": f"{scheme}://{machine.host}{port_str}{path}"
    }


@app.put("/api/apis/{id}")
def update_api(id: int, data: ApiPayload, session: Session = Depends(get_session)):
    api = session.get(ApiProbe, id)
    if not api:
        raise HTTPException(status_code=404, detail="ApiProbe not found")
        
    machine = session.get(MachineNode, data.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Associated MachineNode not found")
        
    old_name = api.name
    api.machine_id = data.machine_id
    api.name = data.name
    api.http_path = data.http_path
    api.http_method = data.http_method
    api.http_headers = data.http_headers
    api.expected_schema = data.expected_schema
    api.cron_interval_minutes = data.cron_interval_minutes
    api.is_active = data.is_active
    api.email_receivers = data.email_receivers
    session.add(api)
    session.commit()
    session.refresh(api)
    add_api_job(api)
    
    # 同步更新对应 MonitorTarget (若匹配)
    targets = session.exec(select(MonitorTarget).where(MonitorTarget.name == old_name)).all()
    for t in targets:
        t.name = api.name
        t.host = machine.host
        t.port = machine.port
        t.http_path = api.http_path
        t.http_method = api.http_method
        t.expected_schema = api.expected_schema
        t.cron_interval_minutes = api.cron_interval_minutes
        t.email_receivers = api.email_receivers
        session.add(t)
        add_target_job(t)
    session.commit()
    
    grp = session.get(ServiceGroup, machine.group_id) if machine.group_id else None
    env = session.get(Environment, grp.environment_id) if grp else None
    scheme = "https" if machine.port == 443 else "http"
    port_str = f":{machine.port}" if machine.port not in [80, 443] else ""
    path = api.http_path if api.http_path.startswith("/") else f"/{api.http_path}"
    
    return {
        "id": api.id,
        "machine_id": api.machine_id,
        "name": api.name,
        "http_path": api.http_path,
        "http_method": api.http_method,
        "expected_schema": api.expected_schema,
        "cron_interval_minutes": api.cron_interval_minutes,
        "is_active": api.is_active,
        "current_status": api.current_status,
        "machine_name": machine.name,
        "machine_host": machine.host,
        "machine_port": machine.port,
        "environment_id": env.id if env else None,
        "environment_name": env.name if env else "默认环境",
        "full_url": f"{scheme}://{machine.host}{port_str}{path}"
    }


@app.delete("/api/apis/{id}")
def delete_api(id: int, session: Session = Depends(get_session)):
    api = session.get(ApiProbe, id)
    if not api:
        raise HTTPException(status_code=404, detail="ApiProbe not found")
    name = api.name
    remove_api_job(id)
    targets = session.exec(select(MonitorTarget).where(MonitorTarget.name == name)).all()
    for t in targets:
        remove_target_job(t.id)
        session.delete(t)
    session.delete(api)
    session.commit()
    return {"status": "ok", "message": f"接口探针 id={id} 已删除"}


@app.post("/api/apis/{id}/trigger")
async def trigger_api_probe(id: int):
    """手动立即触发对指定接口的业务状态与 Schema 契约校验 (带熔断守卫)"""
    try:
        history = await execute_api_probe(id)
        return history
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==========================================================
# 三、 批量复制能力 (将机器 A 上配置的接口一键同步到同分组其他机器)
# ==========================================================

class CloneApisRequest(BaseModel):
    target_machine_ids: List[int]
    override_existing: bool = False


@app.post("/api/machines/{source_machine_id}/clone-apis")
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


# ==========================================================
# 四、 工具与历史指标查询
# ==========================================================

class InferSchemaRequest(BaseModel):
    sample_json: Any
    strict_mode: bool = False


@app.post("/api/tools/infer-schema")
def infer_json_schema(req: InferSchemaRequest):
    """从给定的样本 JSON 中智能推导 Draft-7 JSON Schema 规则"""
    builder = SchemaBuilder()
    builder.add_schema({"$schema": "http://json-schema.org/draft-07/schema#"})
    builder.add_object(req.sample_json)
    schema = builder.to_schema()

    if req.strict_mode:
        def make_strict(sub_schema):
            if isinstance(sub_schema, dict):
                if sub_schema.get("type") == "object":
                    sub_schema["additionalProperties"] = False
                    if "properties" in sub_schema:
                        sub_schema["required"] = list(sub_schema["properties"].keys())
                for v in sub_schema.values():
                    make_strict(v)
            elif isinstance(sub_schema, list):
                for item in sub_schema:
                    make_strict(item)
        make_strict(schema)

    # 兼顾同时支持 res.data 直接使用与 res.data.schema
    return {
        **schema,
        "schema": schema,
        "status": "ok"
    }


class ValidateSchemaRequest(BaseModel):
    sample_json: Any
    expected_schema: Dict[str, Any]


@app.post("/api/tools/validate-schema")
def validate_json_schema(req: ValidateSchemaRequest):
    """在契约实验室中对比样本数据与预期 Schema，返回破坏性突变列表"""
    is_valid, errors = check_schema(req.sample_json, req.expected_schema)
    return {
        "valid": is_valid,
        "errors": errors,
        "error_count": len(errors),
        "status": "ok"
    }


# 机器时序指标
@app.get("/api/machines/{id}/metrics")
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


# 接口探针时序指标
@app.get("/api/apis/{id}/metrics")
def get_api_metrics(id: int, session: Session = Depends(get_session)):
    records = session.exec(
        select(ApiProbeHistory)
        .where(ApiProbeHistory.api_probe_id == id)
        .order_by(ApiProbeHistory.probed_at.desc())
        .limit(100)
    ).all()
    points = [
        {
            "time": r.probed_at.strftime("%H:%M:%S"),
            "http_ms": r.http_latency_ms or 0.0,
            "http_code": r.http_status_code,
            "is_healthy": r.is_healthy,
            "circuit_broken": r.circuit_broken
        }
        for r in reversed(records)
    ]
    return {"api_id": id, "points": points}


# 接口探针历史探测流水记录
@app.get("/api/apis/{id}/history")
def get_api_history(
    id: int,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    api = session.get(ApiProbe, id)
    machine = session.get(MachineNode, api.machine_id) if api else None
    tcp_ok = (machine.current_status != "OFFLINE") if machine else True
    tcp_latency = machine.last_tcp_latency_ms if machine else None

    records = session.exec(
        select(ApiProbeHistory)
        .where(ApiProbeHistory.api_probe_id == id)
        .order_by(ApiProbeHistory.probed_at.desc())
        .limit(limit)
    ).all()

    # 如果 ApiProbeHistory 为空，尝试查找同名的 MonitorTarget 历史记录
    if not records:
        target = None
        if api:
            target = session.exec(select(MonitorTarget).where(MonitorTarget.name == api.name)).first()
        if not target:
            target = session.get(MonitorTarget, id)
        if target:
            target_records = session.exec(
                select(ProbeHistory)
                .where(ProbeHistory.target_id == target.id)
                .order_by(ProbeHistory.probed_at.desc())
                .limit(limit)
            ).all()
            if target_records:
                return [
                    {
                        "id": r.id,
                        "probed_at": r.probed_at.isoformat() if r.probed_at else None,
                        "tcp_ok": r.tcp_ok,
                        "tcp_latency_ms": r.tcp_latency_ms,
                        "http_status_code": r.http_status_code,
                        "http_latency_ms": r.http_latency_ms,
                        "schema_matched": r.schema_matched,
                        "schema_diff_detail": r.schema_diff_detail,
                        "raw_response_snippet": r.raw_response_snippet,
                        "is_healthy": r.is_healthy,
                        "circuit_broken": False
                    }
                    for r in target_records
                ]

    res = []
    for r in records:
        res.append({
            "id": r.id,
            "api_probe_id": r.api_probe_id,
            "machine_id": r.machine_id,
            "circuit_broken": r.circuit_broken,
            "tcp_ok": False if r.circuit_broken else tcp_ok,
            "tcp_latency_ms": None if r.circuit_broken else tcp_latency,
            "http_status_code": r.http_status_code,
            "http_latency_ms": r.http_latency_ms,
            "schema_matched": r.schema_matched,
            "schema_diff_detail": r.schema_diff_detail,
            "raw_response_snippet": r.raw_response_snippet,
            "is_healthy": r.is_healthy,
            "probed_at": r.probed_at.isoformat() if r.probed_at else None
        })
    return res


# ==========================================================
# 五、 向下兼容旧版平铺目标 API (支持老前端和过渡调用)
# ==========================================================

@app.get("/api/targets", response_model=List[MonitorTarget])
def list_targets(
    group: Optional[str] = None,
    session: Session = Depends(get_session)
):
    stmt = select(MonitorTarget)
    if group and group != "ALL":
        stmt = stmt.where(MonitorTarget.group_name == group)
    targets = session.exec(stmt).all()
    for t in targets:
        if t.last_latency_ms is None:
            last_hist = session.exec(
                select(ProbeHistory)
                .where(ProbeHistory.target_id == t.id)
                .order_by(ProbeHistory.id.desc())
            ).first()
            if last_hist:
                t.last_tcp_latency_ms = last_hist.tcp_latency_ms
                t.last_http_latency_ms = last_hist.http_latency_ms
                t.last_latency_ms = last_hist.http_latency_ms or last_hist.tcp_latency_ms
                t.last_probed_at = last_hist.probed_at
    return targets


@app.post("/api/targets", response_model=MonitorTarget)
def create_target(target: MonitorTarget, session: Session = Depends(get_session)):
    session.add(target)
    session.commit()
    session.refresh(target)
    add_target_job(target)
    return target


@app.get("/api/targets/{target_id}", response_model=MonitorTarget)
def get_target(target_id: int, session: Session = Depends(get_session)):
    target = session.get(MonitorTarget, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@app.put("/api/targets/{target_id}", response_model=MonitorTarget)
def update_target(
    target_id: int,
    data: MonitorTarget,
    session: Session = Depends(get_session)
):
    target = session.get(MonitorTarget, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    target.name = data.name
    target.group_name = data.group_name
    target.host = data.host
    target.port = data.port
    target.http_path = data.http_path
    target.http_method = data.http_method
    target.cron_interval_minutes = data.cron_interval_minutes
    target.expected_schema = data.expected_schema
    target.email_receivers = data.email_receivers
    target.is_active = data.is_active
    session.add(target)
    session.commit()
    session.refresh(target)
    add_target_job(target)
    return target


@app.delete("/api/targets/{target_id}")
def delete_target(target_id: int, session: Session = Depends(get_session)):
    target = session.get(MonitorTarget, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    remove_target_job(target_id)
    session.delete(target)
    session.commit()
    return {"status": "ok", "message": f"Target {target_id} deleted"}


@app.post("/api/targets/{target_id}/trigger")
async def trigger_target_probe(target_id: int):
    try:
        history = await execute_probe_for_target(target_id)
        return history
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/metrics/summary")
@app.get("/api/dashboard/summary")
def get_metrics_summary():
    return get_dashboard_summary()


@app.get("/api/targets/{target_id}/metrics")
def get_metrics_by_target(target_id: int):
    return get_target_metrics(target_id)


@app.get("/api/targets/{target_id}/history")
def get_target_history(
    target_id: int,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """获取指定监控目标的历史探测流水记录 (支持展开查看 Schema 差异)"""
    records = session.exec(
        select(ProbeHistory)
        .where(ProbeHistory.target_id == target_id)
        .order_by(ProbeHistory.probed_at.desc())
        .limit(limit)
    ).all()

    if records:
        return [
            {
                "id": r.id,
                "target_id": r.target_id,
                "probed_at": r.probed_at.isoformat() if r.probed_at else None,
                "tcp_ok": r.tcp_ok,
                "tcp_latency_ms": r.tcp_latency_ms,
                "http_status_code": r.http_status_code,
                "http_latency_ms": r.http_latency_ms,
                "schema_matched": r.schema_matched,
                "schema_diff_detail": r.schema_diff_detail,
                "raw_response_snippet": r.raw_response_snippet,
                "is_healthy": r.is_healthy,
                "circuit_broken": False
            }
            for r in records
        ]

    # 如果 ProbeHistory 为空，尝试在 ApiProbeHistory 中查找
    t = session.get(MonitorTarget, target_id)
    api = session.exec(select(ApiProbe).where(ApiProbe.name == t.name)).first() if t else None
    if not api:
        api = session.get(ApiProbe, target_id)
    if api:
        machine = session.get(MachineNode, api.machine_id) if api else None
        tcp_ok = (machine.current_status != "OFFLINE") if machine else True
        tcp_lat = machine.last_tcp_latency_ms if machine else None
        api_records = session.exec(
            select(ApiProbeHistory)
            .where(ApiProbeHistory.api_probe_id == api.id)
            .order_by(ApiProbeHistory.probed_at.desc())
            .limit(limit)
        ).all()
        return [
            {
                "id": r.id,
                "target_id": target_id,
                "probed_at": r.probed_at.isoformat() if r.probed_at else None,
                "circuit_broken": r.circuit_broken,
                "tcp_ok": False if r.circuit_broken else tcp_ok,
                "tcp_latency_ms": None if r.circuit_broken else tcp_lat,
                "http_status_code": r.http_status_code,
                "http_latency_ms": r.http_latency_ms,
                "schema_matched": r.schema_matched,
                "schema_diff_detail": r.schema_diff_detail,
                "raw_response_snippet": r.raw_response_snippet,
                "is_healthy": r.is_healthy
            }
            for r in api_records
        ]
    return []
