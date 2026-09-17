from typing import Dict, Any, List, Optional

from pydantic import BaseModel


class PostmanConfirmImportRequest(BaseModel):
    """Postman 接口确认导入载荷"""
    selected_apis: List[Dict[str, Any]]
    environment_variables: Dict[str, Any] = {}
    postman_base_url: Optional[str] = None
    sync_env_vars: bool = True
    update_machine_base_url: bool = True
    conflict_policy: str = "rename"  # rename | overwrite | skip
    cron_interval_minutes: int = 5
    machine_id: Optional[int] = None
