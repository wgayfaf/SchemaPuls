"""DB Fixture 插件: 数据准备与后置清理核心引擎 (Lifecycle Executor)

在接口或场景执行前连接目标数据库写入 Mock 记录并导出变量供接口消费；
在接口执行结束后 (无论成功、失败或异常)，在 finally 块中自动删除生成的数据。
"""
import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal
from typing import Dict, Any, Optional, List
from sqlmodel import Session

from app.plugins.db_fixture.models import MachineDatabase
from app.plugins.db_fixture.pool_manager import db_pool_manager

logger = logging.getLogger("schemapulse.db_fixture.executor")


def _to_json_safe(obj: Any) -> Any:
    """递归将 datetime, date, UUID, Decimal 等转换为标准 JSON 可序列化类型"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_json_safe(i) for i in obj]
    return obj


@dataclass
class TableFixtureItem:
    """单个数据表的准备结果与销毁跟踪"""
    table_name: str
    primary_key_column: Optional[str] = None
    primary_key_value: Any = None
    inserted_record: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    is_success: bool = False
    prepare_message: str = ""
    cleanup_done: bool = False
    cleanup_message: str = ""
    error: str = ""


@dataclass
class FixtureContext:
    """运行期 DB 环境准备整体上下文对象 (支持多表顺序写入与逆序销毁)"""
    enabled: bool = False
    database_id: Optional[int] = None
    database_name: str = ""
    auto_cleanup: bool = True
    is_success: bool = False
    prepare_message: str = ""
    cleanup_done: bool = False
    cleanup_message: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)

    # 多表明细列表 (按准备顺序记录)
    tables: List[TableFixtureItem] = field(default_factory=list)

    # 兼容单表旧字段 (指向首张或最新表)
    table_name: str = ""
    primary_key_column: Optional[str] = None
    primary_key_value: Any = None
    inserted_record: Dict[str, Any] = field(default_factory=dict)

    @property
    def error_message(self) -> str:
        return "" if self.is_success else self.prepare_message


def _parse_cast_type(udt_name: str, data_type: str) -> str:
    """转换 PostgreSQL 类型强转后缀，防止类型不匹配"""
    udt = (udt_name or "").lower().strip()
    dt = (data_type or "").lower().strip()

    if udt == "uuid" or "uuid" in dt:
        return "::text::uuid"
    if udt == "jsonb" or "jsonb" in dt:
        return "::text::jsonb"
    if udt == "json" or "json" in dt:
        return "::text::json"
    if udt in ("int2", "smallint") or dt in ("int2", "smallint"):
        return "::smallint"
    if udt in ("int4", "integer", "int") or dt in ("int4", "integer", "int"):
        return "::integer"
    if udt in ("int8", "bigint") or dt in ("int8", "bigint"):
        return "::bigint"
    if udt in ("bool", "boolean") or dt in ("bool", "boolean"):
        return "::boolean"
    if udt == "date" or "date" in dt:
        return "::text::date"
    if "timestamptz" in udt or "timestamptz" in dt:
        return "::text::timestamptz"
    if "timestamp" in udt or "timestamp" in dt:
        return "::text::timestamp"
    if udt in ("numeric", "decimal", "float4", "float8", "real", "double precision") or dt in ("numeric", "decimal", "float4", "float8", "real", "double precision"):
        return "::numeric"
    return ""


def _render_field_value_macros(val: Any, accumulated_vars: Dict[str, Any]) -> Any:
    """渲染字段值中的宏与前序表导出的环境变量 (例如 {{env_prepared_users_id}})"""
    if not isinstance(val, str):
        return val

    # 1. 替换平台内置动态宏 (时间戳/UUID/随机数)
    try:
        from app.services.template_engine import render_macro_string
        rendered = render_macro_string(val)
    except Exception:
        rendered = val

    # 2. 替换前序表及环境导出的变量
    if accumulated_vars and isinstance(rendered, str):
        for k, v in accumulated_vars.items():
            pattern = r'\{\{\s*' + re.escape(str(k)) + r'\s*\}\}'
            rendered = re.sub(pattern, str(v) if v is not None else "", rendered)

    return rendered


async def prepare_db_fixture(fixture_config: Optional[Dict[str, Any]], session: Session) -> Optional[FixtureContext]:
    """
    【前置数据准备 (支持多表顺序准备与级联变量传递)】:
    1. 校验配置是否开启
    2. 获取机器关联的目标数据库与连接池
    3. 按序依次向各数据表执行 INSERT ... RETURNING * 插入测试记录
    4. 前序表导出的主键与变量可直接用于后续表的字段值（解决外键依赖）
    5. 汇总所有表的导出变量并注入接口上下文
    """
    if not fixture_config or not isinstance(fixture_config, dict):
        return None

    if not fixture_config.get("enabled", False):
        return None

    database_id = fixture_config.get("database_id")
    if not database_id:
        return None

    # 获取所有待准备的数据表配置列表 (兼容单表与多表)
    raw_tables = fixture_config.get("tables")
    if not raw_tables or not isinstance(raw_tables, list):
        single_table = (fixture_config.get("table_name") or "").strip()
        if single_table:
            raw_tables = [{
                "table_name": single_table,
                "primary_key_column": fixture_config.get("primary_key_column", "id"),
                "fields": fixture_config.get("fields", [])
            }]
        else:
            return None

    valid_tables = [t for t in raw_tables if isinstance(t, dict) and (t.get("table_name") or "").strip()]
    if not valid_tables:
        return None

    db = session.get(MachineDatabase, database_id)
    if not db:
        ctx = FixtureContext(
            enabled=True,
            database_id=database_id,
            is_success=False,
            prepare_message=f"目标数据库配置 (ID: {database_id}) 未找到"
        )
        return ctx

    auto_cleanup = fixture_config.get("auto_cleanup", True)
    ctx = FixtureContext(
        enabled=True,
        database_id=db.id,
        database_name=db.name,
        auto_cleanup=auto_cleanup,
        is_success=True,
        tables=[]
    )

    accumulated_vars: Dict[str, Any] = {}

    try:
        async with db_pool_manager.acquire_connection(db) as conn:
            for tbl_cfg in valid_tables:
                table_name = tbl_cfg["table_name"].strip()
                pk_col = tbl_cfg.get("primary_key_column")
                raw_fields = tbl_cfg.get("fields", [])

                insert_fields = []
                param_values = []
                for f in raw_fields:
                    col_name = f.get("column_name")
                    if not col_name:
                        continue
                    if f.get("include_in_insert", True):
                        raw_val = f.get("value")
                        val = _render_field_value_macros(raw_val, accumulated_vars)

                        # 处理布尔值与数值类型安全转换
                        udt = (f.get("udt_name") or "").lower()
                        dt = (f.get("data_type") or "").lower()
                        is_int_col = (
                            udt in ("int2", "int4", "int8", "smallint", "integer", "bigint", "int") or
                            dt in ("int2", "int4", "int8", "smallint", "integer", "bigint", "int") or
                            col_name.endswith("_id") or col_name == "id"
                        )
                        is_bool_col = (
                            udt in ("bool", "boolean") or
                            dt in ("bool", "boolean")
                        )
                        is_float_col = (
                            udt in ("numeric", "decimal", "float4", "float8", "real", "double precision") or
                            dt in ("numeric", "decimal", "float4", "float8", "real", "double precision")
                        )

                        if is_bool_col and isinstance(val, str):
                            val = val.lower() in ("true", "1", "t", "yes")
                        elif is_int_col and isinstance(val, str) and val.strip().lstrip("-").isdigit():
                            val = int(val.strip())
                        elif is_float_col and isinstance(val, str):
                            try:
                                val = float(val.strip())
                            except ValueError:
                                pass

                        insert_fields.append(f)
                        param_values.append(val)

                if insert_fields:
                    cols_sql = ", ".join([f'"{f["column_name"]}"' for f in insert_fields])
                    placeholders = []
                    for idx, f in enumerate(insert_fields, start=1):
                        cast = _parse_cast_type(f.get("udt_name", ""), f.get("data_type", ""))
                        placeholders.append(f"${idx}{cast}")
                    vals_sql = ", ".join(placeholders)
                    insert_sql = f'INSERT INTO "{table_name}" ({cols_sql}) VALUES ({vals_sql}) RETURNING *;'
                else:
                    insert_sql = f'INSERT INTO "{table_name}" DEFAULT VALUES RETURNING *;'

                try:
                    if insert_fields:
                        row = await conn.fetchrow(insert_sql, *param_values)
                    else:
                        row = await conn.fetchrow(insert_sql)
                except Exception as query_err:
                    err_msg = f"数据表 [{table_name}] 写入执行报错: {str(query_err)}"
                    logger.error(f"[DB Fixture Error] {err_msg}", exc_info=True)
                    item = TableFixtureItem(
                        table_name=table_name,
                        primary_key_column=pk_col,
                        is_success=False,
                        error=str(query_err),
                        prepare_message=err_msg
                    )
                    ctx.tables.append(item)
                    ctx.is_success = False
                    ctx.prepare_message = err_msg
                    if auto_cleanup:
                        await cleanup_db_fixture(ctx, session)
                    return ctx

                if not row:
                    err_msg = f"数据表 [{table_name}] 插入未返回有效记录"
                    item = TableFixtureItem(
                        table_name=table_name,
                        primary_key_column=pk_col,
                        is_success=False,
                        error=err_msg,
                        prepare_message=err_msg
                    )
                    ctx.tables.append(item)
                    ctx.is_success = False
                    ctx.prepare_message = err_msg
                    if auto_cleanup:
                        await cleanup_db_fixture(ctx, session)
                    return ctx

                row_dict = {k: _to_json_safe(v) for k, v in dict(row).items()}

                # 探测主键列
                if not pk_col or pk_col not in row_dict:
                    if "id" in row_dict:
                        pk_col = "id"
                    elif row_dict:
                        pk_col = list(row_dict.keys())[0]

                pk_val = row_dict.get(pk_col)

                # 提取此表导出的变量
                tbl_vars: Dict[str, Any] = {}
                for f in raw_fields:
                    c_name = f.get("column_name")
                    v_name = (f.get("variable_name") or "").strip()
                    if v_name and c_name in row_dict:
                        val = row_dict[c_name]
                        tbl_vars[v_name] = str(val) if val is not None else ""

                if pk_val is not None:
                    tbl_vars[f"{table_name}_id"] = str(pk_val)
                    tbl_vars[f"env_prepared_{table_name}_id"] = str(pk_val)
                    # 全局通用的最新/默认主键 ID
                    tbl_vars["env_prepared_id"] = str(pk_val)

                tbl_vars[f"env_prepared_{table_name}_table"] = table_name

                for k, v in row_dict.items():
                    tbl_vars[f"env_prepared_{table_name}_{k}"] = str(v) if v is not None else ""
                    if f"env_prepared_{k}" not in accumulated_vars and f"env_prepared_{k}" not in tbl_vars:
                        tbl_vars[f"env_prepared_{k}"] = str(v) if v is not None else ""

                accumulated_vars.update(tbl_vars)

                msg = f"成功向 [{table_name}] 插入测试数据，主键 [{pk_col}]: {pk_val}"
                logger.info(f"[DB Fixture] {msg}")

                item = TableFixtureItem(
                    table_name=table_name,
                    primary_key_column=pk_col,
                    primary_key_value=pk_val,
                    inserted_record=row_dict,
                    variables=tbl_vars,
                    is_success=True,
                    prepare_message=msg
                )
                ctx.tables.append(item)

        ctx.is_success = True
        ctx.variables = accumulated_vars
        success_names = [f"{t.table_name}({t.primary_key_column}:{t.primary_key_value})" for t in ctx.tables if t.is_success]
        ctx.prepare_message = f"成功完成 {len(ctx.tables)} 张数据表准备: " + ", ".join(success_names)

        # 兼容单表旧字段 (取首张表)
        if ctx.tables:
            first_t = ctx.tables[0]
            ctx.table_name = first_t.table_name
            ctx.primary_key_column = first_t.primary_key_column
            ctx.primary_key_value = first_t.primary_key_value
            ctx.inserted_record = first_t.inserted_record

        return ctx

    except Exception as e:
        err_msg = f"环境数据准备失败: {str(e)}"
        logger.error(f"[DB Fixture Error] {err_msg}", exc_info=True)
        ctx.is_success = False
        ctx.prepare_message = err_msg
        if auto_cleanup:
            await cleanup_db_fixture(ctx, session)
        return ctx


async def cleanup_db_fixture(ctx: Optional[FixtureContext], session: Session) -> Dict[str, Any]:
    """
    【后置数据清理 (支持多表逆序销毁，保证外键约束完整)】:
    无论接口调用成功还是失败，均在 finally 中执行该操作，彻底物理删除插入的测试记录，防污染测试库
    """
    if not ctx or not ctx.enabled or not ctx.auto_cleanup:
        return {"cleaned": False, "reason": "未启用或未配置自动清理"}

    db = session.get(MachineDatabase, ctx.database_id)
    if not db:
        ctx.cleanup_done = False
        ctx.cleanup_message = f"清理失败: 未找到数据库配置 (ID: {ctx.database_id})"
        return {"cleaned": False, "error": ctx.cleanup_message}

    # 收集需要删除的表记录 (必须以逆序进行，避免外键依赖约束报错)
    targets_to_delete = [
        t for t in reversed(ctx.tables)
        if t.is_success and t.table_name and t.primary_key_column and t.primary_key_value is not None and not t.cleanup_done
    ]

    # 兼容旧单表模式
    if not targets_to_delete and ctx.is_success and ctx.table_name and ctx.primary_key_column and ctx.primary_key_value is not None and not ctx.cleanup_done:
        targets_to_delete = [
            TableFixtureItem(
                table_name=ctx.table_name,
                primary_key_column=ctx.primary_key_column,
                primary_key_value=ctx.primary_key_value,
                is_success=True
            )
        ]

    if not targets_to_delete:
        return {"cleaned": False, "reason": "无有效的主键记录可供清理"}

    cleaned_names = []
    errors = []

    try:
        async with db_pool_manager.acquire_connection(db) as conn:
            for t in targets_to_delete:
                try:
                    delete_sql = f'DELETE FROM "{t.table_name}" WHERE "{t.primary_key_column}" = $1;'
                    await conn.execute(delete_sql, t.primary_key_value)
                    t.cleanup_done = True
                    t.cleanup_message = f"已删除表 [{t.table_name}] 记录 ({t.primary_key_column}={t.primary_key_value})"
                    cleaned_names.append(f"{t.table_name}(ID:{t.primary_key_value})")
                    logger.info(f"[DB Fixture Cleanup] {t.cleanup_message}")
                except Exception as e:
                    t.cleanup_done = False
                    t.cleanup_message = f"删除表 [{t.table_name}] 记录失败: {str(e)}"
                    errors.append(t.cleanup_message)
                    logger.warning(f"[DB Fixture Cleanup Warning] {t.cleanup_message}")

        if errors:
            ctx.cleanup_done = False
            ctx.cleanup_message = "; ".join(errors)
            return {"cleaned": False, "error": ctx.cleanup_message}
        else:
            ctx.cleanup_done = True
            ctx.cleanup_message = f"已成功物理删除 {len(cleaned_names)} 张表测试数据: " + ", ".join(cleaned_names)
            return {"cleaned": True, "message": ctx.cleanup_message}

    except Exception as pool_err:
        ctx.cleanup_done = False
        ctx.cleanup_message = f"连接数据库执行清理异常: {str(pool_err)}"
        return {"cleaned": False, "error": ctx.cleanup_message}

