"""向下兼容旧版平铺目标 API (支持老前端和过渡调用) 与大盘指标"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import (
    MonitorTarget, ProbeHistory, MachineNode, ApiProbe, ApiProbeHistory,
)
from app.services.probe_service import execute_probe_for_target
from app.services.scheduler import add_target_job, remove_target_job
from app.services.metric_service import get_dashboard_summary, get_target_metrics

router = APIRouter(tags=["targets-legacy"])


@router.get("/api/targets", response_model=List[MonitorTarget])
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


@router.post("/api/targets", response_model=MonitorTarget)
def create_target(target: MonitorTarget, session: Session = Depends(get_session)):
    session.add(target)
    session.commit()
    session.refresh(target)
    add_target_job(target)
    return target


@router.get("/api/targets/{target_id}", response_model=MonitorTarget)
def get_target(target_id: int, session: Session = Depends(get_session)):
    target = session.get(MonitorTarget, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@router.put("/api/targets/{target_id}", response_model=MonitorTarget)
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


@router.delete("/api/targets/{target_id}")
def delete_target(target_id: int, session: Session = Depends(get_session)):
    target = session.get(MonitorTarget, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    remove_target_job(target_id)
    session.delete(target)
    session.commit()
    return {"status": "ok", "message": f"Target {target_id} deleted"}


@router.post("/api/targets/{target_id}/trigger")
async def trigger_target_probe(target_id: int):
    try:
        history = await execute_probe_for_target(target_id)
        return history
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/metrics/summary")
@router.get("/api/dashboard/summary")
def get_metrics_summary():
    return get_dashboard_summary()


@router.get("/api/targets/{target_id}/metrics")
def get_metrics_by_target(target_id: int):
    return get_target_metrics(target_id)


@router.get("/api/targets/{target_id}/history")
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
