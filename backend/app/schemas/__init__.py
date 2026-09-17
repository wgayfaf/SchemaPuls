"""请求/响应 Pydantic 模型统一出口 (从原 main.py 中抽出，按领域拆分)"""
from app.schemas.environment import EnvironmentVariablesPayload
from app.schemas.machine import MachinePayload, CloneApisRequest
from app.schemas.api_probe import ApiPayload, ApiTestRunPayload
from app.schemas.tools import InferSchemaRequest, ValidateSchemaRequest
from app.schemas.postman import PostmanConfirmImportRequest

__all__ = [
    "EnvironmentVariablesPayload",
    "MachinePayload",
    "CloneApisRequest",
    "ApiPayload",
    "ApiTestRunPayload",
    "InferSchemaRequest",
    "ValidateSchemaRequest",
    "PostmanConfirmImportRequest",
]
