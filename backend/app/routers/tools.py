"""工具接口：JSON Schema 智能推导与契约校验"""
from fastapi import APIRouter

from genson import SchemaBuilder

from app.schemas.tools import InferSchemaRequest, ValidateSchemaRequest
from app.services.probe_service import check_schema

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.post("/infer-schema")
def infer_json_schema(req: InferSchemaRequest):
    """从给定的样本 JSON 中智能推导 Draft-7 JSON Schema 规则"""
    builder = SchemaBuilder()
    builder.add_schema({"$schema": "http://json-schema.org/draft-07/schema#"})
    builder.add_object(req.sample_json)
    schema = builder.to_schema()

    if req.strict_mode:
        def make_strict(sub_schema):
            if isinstance(sub_schema, dict):
                if sub_schema.get("type") == "object":
                    sub_schema["additionalProperties"] = False
                    if "properties" in sub_schema:
                        sub_schema["required"] = list(sub_schema["properties"].keys())
                for v in sub_schema.values():
                    make_strict(v)
            elif isinstance(sub_schema, list):
                for item in sub_schema:
                    make_strict(item)
        make_strict(schema)

    # 兼顾同时支持 res.data 直接使用与 res.data.schema
    return {
        **schema,
        "schema": schema,
        "status": "ok"
    }


@router.post("/validate-schema")
def validate_json_schema(req: ValidateSchemaRequest):
    """在契约实验室中对比样本数据与预期 Schema，返回破坏性突变列表"""
    is_valid, errors = check_schema(req.sample_json, req.expected_schema)
    return {
        "valid": is_valid,
        "errors": errors,
        "error_count": len(errors),
        "status": "ok"
    }
