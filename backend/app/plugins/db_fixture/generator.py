"""DB Fixture 插件: PostgreSQL 字段类型智能 Mock 数据生成器"""
import uuid
import time
import random
import json
from datetime import datetime
from typing import Dict, Any, List, Optional


def generate_value_for_column(col: Dict[str, Any]) -> Any:
    """根据 PostgreSQL 字段元数据 (udt_name, data_type, column_name, max_length) 智能生成契合的测试值"""
    col_name = (col.get("column_name") or "").lower()
    udt = (col.get("udt_name") or "").lower()
    data_type = (col.get("data_type") or "").lower()
    max_len = col.get("max_length")

    rand_int = random.randint(1000, 9999)

    # 1. UUID 类型
    if udt == "uuid" or "uuid" in data_type:
        return str(uuid.uuid4())

    # 2. 布尔类型
    if udt in ("bool", "boolean") or "bool" in data_type:
        return True

    # 3. 整型 / Bigint / Smallint
    if udt in ("int2", "int4", "int8", "smallint", "integer", "bigint", "serial", "bigserial") or "int" in data_type:
        if col.get("is_primary_key") and col.get("has_default"):
            # 自增主键推荐由序列自增生成，但若显式提供，生成高位隔离整型
            return int(time.time() % 1000000) + rand_int
        if "status" in col_name or "state" in col_name:
            return 1
        if "age" in col_name:
            return 25
        if "sort" in col_name or "order" in col_name:
            return 10
        return rand_int

    # 4. 浮点/数值/高精度 Decimal
    if udt in ("numeric", "decimal", "float4", "float8", "real", "double precision") or "numeric" in data_type:
        precision = col.get("numeric_precision") or 10
        scale = col.get("numeric_scale") or 2
        return round(99.99, scale)

    # 5. 时间与日期
    now = datetime.now()
    if "timestamptz" in udt or "timestamptz" in data_type or udt in ("timestamp", "timestamptz"):
        return now.strftime("%Y-%m-%d %H:%M:%S")
    if udt == "date" or "date" in data_type:
        return now.strftime("%Y-%m-%d")
    if udt in ("time", "timetz") or "time" in data_type:
        return now.strftime("%H:%M:%S")

    # 6. JSON / JSONB
    if udt in ("json", "jsonb") or "json" in data_type:
        mock_payload = {
            "source": "schemapulse_fixture",
            "test_flag": True,
            "mock_id": rand_int
        }
        return json.dumps(mock_payload, ensure_ascii=False)

    # 7. 文本/字符 (varchar, text, char)
    val = ""
    if "email" in col_name or "mail" in col_name:
        val = f"fixture_{rand_int}@example.com"
    elif "phone" in col_name or "mobile" in col_name or "tel" in col_name:
        val = f"138{random.randint(10000000, 99999999)}"
    elif "username" in col_name or "user_name" in col_name:
        val = f"test_user_{rand_int}"
    elif "name" in col_name:
        val = f"测试数据_{rand_int}"
    elif "code" in col_name:
        val = f"CODE_{rand_int}"
    elif "url" in col_name or "link" in col_name:
        val = f"https://example.com/test/{rand_int}"
    elif "ip" in col_name:
        val = "127.0.0.1"
    elif "token" in col_name:
        val = f"fixture_token_{uuid.uuid4().hex[:16]}"
    elif "password" in col_name or "pwd" in col_name:
        val = "TestPass@123"
    elif "status" in col_name or "state" in col_name:
        val = "ACTIVE"
    elif "description" in col_name or "remark" in col_name or "comment" in col_name:
        val = "SchemaPulse 自动化拨测临时测试数据"
    else:
        val = f"mock_{col.get('column_name')}_{rand_int}"

    # 若有限定最大长度，进行安全裁剪
    if max_len and isinstance(max_len, int) and len(val) > max_len:
        val = val[:max_len]

    return val


def generate_mock_data_for_table(schema_info: Dict[str, Any]) -> Dict[str, Any]:
    """基于表字段架构生成完整的测试数据模版及变量映射建议"""
    table_name = schema_info.get("table_name", "")
    columns = schema_info.get("columns", [])
    primary_keys = schema_info.get("primary_keys", [])
    primary_key_column = schema_info.get("primary_key_column")

    fields = []
    for col in columns:
        col_name = col.get("column_name")
        is_pk = col.get("is_primary_key", False)
        has_default = col.get("has_default", False)
        col_def = (col.get("column_default") or "").lower()

        # 字段是否默认参与插入判定逻辑:
        # 1. 自增主键/有默认值的主键 -> False (由数据库自增生成)
        # 2. 具有默认值的非主键字段 -> False (优先采用数据库默认值，防破坏 check 约束/默认逻辑，用户可自主勾选覆盖)
        # 3. 非空且无默认值的字段 -> True (必填字段，必须插入)
        # 4. 可空且无默认值的字段 -> True (提供测试数据)
        is_auto_increment = is_pk and ("nextval" in col_def or "gen_random_uuid" in col_def)
        if is_pk:
            include_in_insert = not (is_auto_increment or has_default)
        elif has_default:
            include_in_insert = False
        else:
            include_in_insert = True

        mock_val = generate_value_for_column(col)

        # 推荐变量名称 (多表场景下带表名前缀，防止字段重名冲突)
        if is_pk:
            var_name = f"env_prepared_{table_name}_id"
        else:
            var_name = f"env_prepared_{table_name}_{col_name}"

        fields.append({
            "column_name": col_name,
            "data_type": col.get("data_type"),
            "udt_name": col.get("udt_name"),
            "is_primary_key": is_pk,
            "is_nullable": col.get("is_nullable", True),
            "has_default": has_default,
            "is_auto_increment": is_auto_increment,
            "include_in_insert": include_in_insert,
            "value": mock_val,
            "variable_name": var_name
        })

    return {
        "table_name": table_name,
        "primary_keys": primary_keys,
        "primary_key_column": primary_key_column,
        "auto_cleanup": True,
        "fields": fields
    }
