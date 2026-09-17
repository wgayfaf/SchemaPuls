"""分组层 CRUD"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import Environment, ServiceGroup, MachineNode, ApiProbe
from app.services.scheduler import remove_machine_job, remove_api_job

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("", response_model=List[ServiceGroup])
def list_service_groups(environment_id: Optional[int] = None, session: Session = Depends(get_session)):
    stmt = select(ServiceGroup)
    if environment_id:
        stmt = stmt.where(ServiceGroup.environment_id == environment_id)
    return session.exec(stmt).all()


@router.post("", response_model=ServiceGroup)
def create_service_group(group: ServiceGroup, session: Session = Depends(get_session)):
    env = session.get(Environment, group.environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Associated Environment not found")
    session.add(group)
    session.commit()
    session.refresh(group)
    return group


@router.put("/{id}", response_model=ServiceGroup)
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


@router.delete("/{id}")
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
