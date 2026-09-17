"""树状拓扑聚合接口 (供前端一次性拉取整棵拓扑树)"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import Environment, ServiceGroup, MachineNode, ApiProbe

router = APIRouter(tags=["topology"])


@router.get("/api/topology/tree")
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
