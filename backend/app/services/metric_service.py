from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from sqlmodel import Session, select, func
from app.models import MonitorTarget, ProbeHistory
from app.database import engine


def get_dashboard_summary() -> Dict[str, Any]:
    """计算监控大盘概览统计指标"""
    with Session(engine) as session:
        targets = session.exec(select(MonitorTarget)).all()
        total_targets = len(targets)
        healthy_count = sum(1 for t in targets if t.current_status == "HEALTHY")
        down_count = sum(1 for t in targets if t.current_status == "DOWN")
        degraded_count = sum(1 for t in targets if t.current_status == "DEGRADED")
        unknown_count = sum(1 for t in targets if t.current_status == "UNKNOWN")

        # 计算近 24 小时的 SLA 可用率
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        total_probes = session.exec(
            select(func.count(ProbeHistory.id)).where(ProbeHistory.probed_at >= since)
        ).one() or 0

        healthy_probes = session.exec(
            select(func.count(ProbeHistory.id))
            .where(ProbeHistory.probed_at >= since)
            .where(ProbeHistory.is_healthy == True)
        ).one() or 0

        sla_rate = round((healthy_probes / total_probes * 100), 2) if total_probes > 0 else 100.0

        return {
            "total_targets": total_targets,
            "healthy_count": healthy_count,
            "down_count": down_count,
            "degraded_count": degraded_count,
            "unknown_count": unknown_count,
            "total_probes_24h": total_probes,
            "sla_rate": sla_rate
        }


def get_target_metrics(target_id: int, hours: int = 24) -> List[Dict[str, Any]]:
    """获取指定监控节点近 N 小时的时序指标点位 (供 ECharts 绘图)"""
    with Session(engine) as session:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = (
            select(ProbeHistory)
            .where(ProbeHistory.target_id == target_id)
            .where(ProbeHistory.probed_at >= since)
            .order_by(ProbeHistory.probed_at.asc())
        )
        records = session.exec(query).all()

        points = []
        for r in records:
            points.append({
                "id": r.id,
                "time": r.probed_at.strftime("%H:%M:%S"),
                "timestamp": r.probed_at.isoformat(),
                "tcp_ms": r.tcp_latency_ms if r.tcp_ok else None,
                "http_ms": r.http_latency_ms if r.http_status_code else None,
                "http_code": r.http_status_code,
                "is_healthy": r.is_healthy,
                "schema_matched": r.schema_matched
            })
        return points
