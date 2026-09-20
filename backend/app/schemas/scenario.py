from typing import Dict, Any, List, Optional

from pydantic import BaseModel


class ScenarioStepPayload(BaseModel):
    """场景拨测单步骤 (业务链路节点) 配置"""
    name: Optional[str] = ""
    http_method: str = "GET"
    http_path: str = "/"
    http_params: List[Dict[str, Any]] = []
    http_headers: List[Dict[str, Any]] = []
    http_body_type: str = "none"
    http_body: Optional[str] = None
    is_cleanup: bool = False  # 清理步骤: 拨测引擎将保证无论成败均执行 (finally 语义)


class ScenarioPayload(BaseModel):
    """场景拨测创建/更新载荷"""
    machine_id: int
    name: str
    description: Optional[str] = None
    base_url: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    cron_interval_minutes: int = 5
    is_active: bool = True


class ScenarioStepTestPayload(BaseModel):
    """场景单节点无状态调试载荷 (新建/编辑场景对话框中的发送调试)"""
    machine_id: int
    base_url: Optional[str] = None
    step: Dict[str, Any] = {}
