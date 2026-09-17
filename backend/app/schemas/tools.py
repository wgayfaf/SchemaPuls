from typing import Any, Dict

from pydantic import BaseModel


class InferSchemaRequest(BaseModel):
    """JSON Schema 智能推导请求"""
    sample_json: Any
    strict_mode: bool = False


class ValidateSchemaRequest(BaseModel):
    """Schema 契约校验请求"""
    sample_json: Any
    expected_schema: Dict[str, Any]
