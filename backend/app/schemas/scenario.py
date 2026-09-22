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
    variables: Dict[str, Any] = {} # 场景专属初始变量池 (仅限当前场景生效, 隔离防污染)
    cron_interval_minutes: int = 5
    is_active: bool = True


class ScenarioStepTestPayload(BaseModel):
    """场景单节点无状态调试载荷 (新建/编辑场景对话框中的发送调试)"""
    machine_id: int
    base_url: Optional[str] = None
    step: Dict[str, Any] = {}
    scenario_variables: Dict[str, Any] = {} # 场景专属变量上下文 (调试时注入)


class BatchScenarioIdsPayload(BaseModel):
    """批量场景操作载荷 (批量删除等)"""
    ids: List[int]


class BatchScenarioToggleActivePayload(BaseModel):
    """批量切换/启用/关闭场景定时调度周期载荷"""
    ids: List[int]
    is_active: Optional[bool] = None  # None: 取反切换; True: 批量开启; False: 批量关闭


class BatchScenarioSetIntervalPayload(BaseModel):
    """批量设置场景定时调度周期载荷"""
    ids: List[int]
    cron_interval_minutes: int
