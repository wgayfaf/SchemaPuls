"""场景拨测层 CRUD + 拨测执行引擎接口 (业务链路多步骤拨测)
  - POST   /{id}/run      手动立即执行整链拨测
  - GET    /{id}/history  场景拨测历史流水
  - POST   /test-step     单节点无状态调试 (新建场景对话框中的发送调试)
"""
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import Environment, ServiceGroup, MachineNode, ScenarioProbe, ScenarioProbeHistory
from app.schemas.scenario import ScenarioPayload, ScenarioStepTestPayload
from app.services.scheduler import add_scenario_job, remove_scenario_job
from app.services.scenario_service import (
    execute_scenario_probe,
    execute_scenario_step,
    serialize_scenario_history,
)

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


def _serialize(s: ScenarioProbe, session: Session) -> dict:
    m = session.get(MachineNode, s.machine_id)
    grp = session.get(ServiceGroup, m.group_id) if m and m.group_id else None
    env = session.get(Environment, grp.environment_id) if grp else None
    return {
        "id": s.id,
        "machine_id": s.machine_id,
        "name": s.name,
        "description": s.description,
        "base_url": s.base_url,
        "steps": s.steps or [],
        "step_count": len(s.steps or []),
        "cleanup_step_count": len([x for x in (s.steps or []) if x.get("is_cleanup")]),
        "cron_interval_minutes": s.cron_interval_minutes,
        "is_active": s.is_active,
        "current_status": s.current_status,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "last_total_latency_ms": s.last_total_latency_ms,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "machine_name": m.name if m else "-",
        "machine_host": m.host if m else None,
        "machine_port": m.port if m else None,
        "machine_status": m.current_status if m else "UNKNOWN",
        "environment_id": env.id if env else None,
        "environment_name": env.name if env else "默认环境",
    }


@router.get("")
def list_scenarios(session: Session = Depends(get_session)):
    items = session.exec(select(ScenarioProbe).order_by(ScenarioProbe.id.desc())).all()
    return [_serialize(s, session) for s in items]


@router.post("")
def create_scenario(data: ScenarioPayload, session: Session = Depends(get_session)):
    machine = session.get(MachineNode, data.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Associated MachineNode not found")
    if not data.steps:
        raise HTTPException(status_code=400, detail="场景至少需要一个业务链路步骤")

    scenario = ScenarioProbe(
        machine_id=data.machine_id,
        name=data.name,
        description=data.description,
        base_url=data.base_url,
        steps=data.steps,
        cron_interval_minutes=data.cron_interval_minutes,
        is_active=data.is_active
    )
    session.add(scenario)
    session.commit()
    session.refresh(scenario)
    # 注册定时拨测任务 (启用中的场景立即执行首次拨测并按周期持续巡检)
    add_scenario_job(scenario)
    return _serialize(scenario, session)


@router.put("/{id}")
def update_scenario(id: int, data: ScenarioPayload, session: Session = Depends(get_session)):
    scenario = session.get(ScenarioProbe, id)
    if not scenario:
        raise HTTPException(status_code=404, detail="ScenarioProbe not found")
    if not data.steps:
        raise HTTPException(status_code=400, detail="场景至少需要一个业务链路步骤")

    scenario.machine_id = data.machine_id
    scenario.name = data.name
    scenario.description = data.description
    scenario.base_url = data.base_url
    scenario.steps = data.steps
    scenario.cron_interval_minutes = data.cron_interval_minutes
    scenario.is_active = data.is_active
    session.add(scenario)
    session.commit()
    session.refresh(scenario)
    # 重新注册定时拨测任务 (周期/启停变更后立即生效)
    add_scenario_job(scenario)
    return _serialize(scenario, session)


@router.delete("/{id}")
def delete_scenario(id: int, session: Session = Depends(get_session)):
    scenario = session.get(ScenarioProbe, id)
    if not scenario:
        raise HTTPException(status_code=404, detail="ScenarioProbe not found")
    session.delete(scenario)
    session.commit()
    remove_scenario_job(id)
    return {"detail": f"场景 [{scenario.name}] 已删除"}


# ==========================================================
# 拨测执行引擎接口
# ==========================================================

@router.post("/{id}/run")
async def run_scenario(id: int, session: Session = Depends(get_session)):
    """手动立即执行整链场景拨测 (业务节点串行 + 清理节点 finally 保障)"""
    try:
        history = await execute_scenario_probe(id, trigger="manual")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    scenario = session.get(ScenarioProbe, id)
    return {
        "history": serialize_scenario_history(history),
        "scenario": _serialize(scenario, session) if scenario else None
    }


@router.get("/{id}/history")
def list_scenario_history(
    id: int,
    limit: int = 50,
    session: Session = Depends(get_session)
):
    """获取场景拨测历史流水 (默认最近 50 条, 倒序)"""
    scenario = session.get(ScenarioProbe, id)
    if not scenario:
        raise HTTPException(status_code=404, detail="ScenarioProbe not found")
    items = session.exec(
        select(ScenarioProbeHistory)
        .where(ScenarioProbeHistory.scenario_id == id)
        .order_by(ScenarioProbeHistory.probed_at.desc())
        .limit(max(1, min(limit, 200)))
    ).all()
    return [serialize_scenario_history(h) for h in items]


@router.post("/test-step")
async def test_scenario_step(data: ScenarioStepTestPayload, session: Session = Depends(get_session)):
    """单节点无状态调试: 在场景编排对话框中即时发包验证单个节点配置 (不落库不回写状态)"""
    machine = session.get(MachineNode, data.machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail="Associated MachineNode not found")

    grp = session.get(ServiceGroup, machine.group_id) if machine.group_id else None
    env = session.get(Environment, grp.environment_id) if grp and grp.environment_id else None
    env_variables = dict(env.variables or {}) if env and env.variables else {}

    from app.services.scenario_service import _resolve_base_url
    base_url = _resolve_base_url(data.base_url, machine)

    variable_pool: Dict[str, Any] = dict(env_variables)
    result, updated_env = await execute_scenario_step(
        data.step or {}, base_url, variable_pool, step_index=0
    )

    # 调试产生的环境变量更新同样同步持久化 (与接口管理 test-run 行为一致)
    if updated_env and env:
        from sqlalchemy.orm.attributes import flag_modified
        current_vars = dict(env.variables or {})
        current_vars.update(updated_env)
        env.variables = current_vars
        flag_modified(env, "variables")
        session.add(env)
        session.commit()
        variable_pool.update(updated_env)

    return {
        **result,
        "environment": {
            "id": env.id if env else None,
            "name": env.name if env else "默认环境",
            "variables": variable_pool,
            "updated_variables": updated_env
        }
    }
