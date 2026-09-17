from typing import Dict, Any, List, Optional, Union

from pydantic import BaseModel


class ApiPayload(BaseModel):
    """接口探针创建/更新载荷"""
    machine_id: int
    name: str
    base_url: Optional[str] = None
    http_path: str = "/health"
    http_method: str = "GET"
    http_params: List[Dict[str, Any]] = []
    http_headers: Union[List[Dict[str, Any]], Dict[str, Any], None] = []
    http_body_type: str = "none"
    http_body: Optional[str] = None
    auth_type: str = "none"
    auth_config: Optional[Dict[str, Any]] = {}
    expected_schema: Dict[str, Any]
    pre_actions: List[Dict[str, Any]] = []
    post_actions: List[Dict[str, Any]] = []
    cron_interval_minutes: int = 5
    is_active: bool = True
    email_receivers: List[str] = []
    retry_threshold: int = 3
    silence_minutes: int = 30


class ApiTestRunPayload(BaseModel):
    """即时在线调试运行载荷 (Postman 风格)"""
    machine_id: int
    base_url: Optional[str] = None
    http_method: str = "GET"
    http_path: str = "/health"
    http_params: List[Dict[str, Any]] = []
    http_headers: Union[List[Dict[str, Any]], Dict[str, Any], None] = []
    http_body_type: str = "none"
    http_body: Optional[str] = None
    auth_type: str = "none"
    auth_config: Optional[Dict[str, Any]] = {}
    expected_schema: Optional[Dict[str, Any]] = None
    pre_actions: Optional[List[Dict[str, Any]]] = []
    post_actions: Optional[List[Dict[str, Any]]] = []
