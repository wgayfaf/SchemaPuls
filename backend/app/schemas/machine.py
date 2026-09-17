from typing import List, Optional

from pydantic import BaseModel


class MachinePayload(BaseModel):
    """机器节点创建/更新载荷"""
    name: str
    host: str
    port: int
    base_url: Optional[str] = None  # 机器默认服务基准地址 (如 https://api.prod.com 或 http://192.168.1.10:8080)
    environment_id: Optional[int] = None
    group_id: Optional[int] = None
    cron_interval_minutes: int = 5
    is_active: bool = True
    email_receivers: List[str] = []
    retry_threshold: int = 3
    silence_minutes: int = 30


class CloneApisRequest(BaseModel):
    """批量克隆接口探针载荷"""
    target_machine_ids: List[int]
    override_existing: bool = False
