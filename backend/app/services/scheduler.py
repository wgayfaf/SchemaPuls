from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import Session, select
from app.models import MachineNode, ApiProbe, MonitorTarget
from app.database import engine
from app.services.probe_service import (
    execute_machine_probe,
    execute_api_probe,
    execute_probe_for_target
)
from datetime import datetime
import asyncio

scheduler = AsyncIOScheduler()


# ==========================================================
# 定时执行回调
# ==========================================================

async def scheduled_machine_job(machine_id: int):
    """机器节点定时探测"""
    try:
        await execute_machine_probe(machine_id)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[Scheduler Machine Error] Node {machine_id}: {e}")


async def scheduled_api_job(api_id: int):
    """接口探针定时探测 (带熔断短路守卫)"""
    try:
        await execute_api_probe(api_id)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[Scheduler Api Error] Probe {api_id}: {e}")


async def scheduled_probe_job(target_id: int):
    """向下兼容老版目标定时探测"""
    try:
        await execute_probe_for_target(target_id)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[Scheduler Target Error] Target {target_id}: {e}")


# ==========================================================
# 任务动态注册与注销
# ==========================================================

def add_machine_job(machine: MachineNode):
    """向调度器添加或更新一个机器节点的定时任务 (立即探活并按周期持续巡检)"""
    job_id = f"probe_machine_{machine.id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        
    if machine.is_active:
        interval = max(1, machine.cron_interval_minutes or 1)
        scheduler.add_job(
            scheduled_machine_job,
            "interval",
            minutes=interval,
            next_run_time=datetime.now(),
            args=[machine.id],
            id=job_id,
            replace_existing=True
        )
        print(f"[Scheduler] Registered machine node [{machine.name}] every {interval}m (Initial probe queued immediately)")


def remove_machine_job(machine_id: int):
    """移除机器节点的定时任务"""
    job_id = f"probe_machine_{machine_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        print(f"[Scheduler] Removed machine node id={machine_id}")


def add_api_job(api: ApiProbe):
    """向调度器添加或更新一个接口探针的定时任务 (立即探活并按周期持续巡检)"""
    job_id = f"probe_api_{api.id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        
    if api.is_active:
        interval = max(1, api.cron_interval_minutes or 1)
        scheduler.add_job(
            scheduled_api_job,
            "interval",
            minutes=interval,
            next_run_time=datetime.now(),
            args=[api.id],
            id=job_id,
            replace_existing=True
        )
        print(f"[Scheduler] Registered api probe [{api.name}] every {interval}m (Initial probe queued immediately)")


def remove_api_job(api_id: int):
    """移除接口探针的定时任务"""
    job_id = f"probe_api_{api_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        print(f"[Scheduler] Removed api probe id={api_id}")


def add_target_job(target: MonitorTarget):
    """向下兼容老版平铺目标任务"""
    job_id = f"probe_target_{target.id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    if target.is_active:
        interval = max(1, target.cron_interval_minutes or 1)
        scheduler.add_job(
            scheduled_probe_job,
            "interval",
            minutes=interval,
            next_run_time=datetime.now(),
            args=[target.id],
            id=job_id,
            replace_existing=True
        )


def remove_target_job(target_id: int):
    job_id = f"probe_target_{target_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


# ==========================================================
# 调度器初始化
# ==========================================================

def init_scheduler():
    """系统启动时加载所有启用的机器节点与接口探针"""
    with Session(engine) as session:
        # 加载四层模型机器节点
        machines = session.exec(select(MachineNode).where(MachineNode.is_active == True)).all()
        for m in machines:
            add_machine_job(m)

        # 加载四层模型接口探针
        apis = session.exec(select(ApiProbe).where(ApiProbe.is_active == True)).all()
        for a in apis:
            add_api_job(a)

        # 加载兼容老版目标
        targets = session.exec(select(MonitorTarget).where(MonitorTarget.is_active == True)).all()
        for t in targets:
            add_target_job(t)
    
    if not scheduler.running:
        scheduler.start()
        print("[Scheduler] Started APScheduler engine successfully.")
