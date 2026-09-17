from typing import Dict, Any

from pydantic import BaseModel


class EnvironmentVariablesPayload(BaseModel):
    """环境变量池整体更新载荷"""
    variables: Dict[str, Any]
