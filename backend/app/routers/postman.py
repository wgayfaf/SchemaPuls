"""Postman 格式数据导入 (按机器节点关联导入)"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlmodel import Session

from app.database import get_session
from app.models import MachineNode
from app.schemas.postman import PostmanConfirmImportRequest
from app.services.postman_importer import parse_postman_package, import_postman_to_machine

router = APIRouter(tags=["postman-import"])


@router.post("/api/machines/{machine_id}/import-postman/preview")
async def preview_postman_import_for_machine(
    machine_id: int,
    file: Optional[UploadFile] = File(None),
    raw_json: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    """
    针对指定机器节点，上传 Postman 文件 (.zip / .json) 或 JSON 文本进行智能解析预览
    """
    machine = session.get(MachineNode, machine_id)
    if not machine:
        raise HTTPException(status_code=404, detail=f"指定机器节点不存在 (ID: {machine_id})")

    file_bytes = b""
    filename = ""
    if file:
        file_bytes = await file.read()
        filename = file.filename or ""
    elif raw_json:
        file_bytes = raw_json.encode("utf-8")
        filename = "content.json"
    else:
        raise HTTPException(status_code=400, detail="请上传 Postman 格式文件 (.zip / .json) 或提供 JSON 文本内容")

    try:
        parsed = parse_postman_package(file_bytes, filename, machine.base_url)
        return {
            "success": True,
            "machine": {
                "id": machine.id,
                "name": machine.name,
                "base_url": machine.base_url
            },
            "data": parsed
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Postman 文件解析失败: {str(e)}")


@router.post("/api/machines/{machine_id}/import-postman/confirm")
def confirm_postman_import_for_machine(
    machine_id: int,
    req: PostmanConfirmImportRequest,
    session: Session = Depends(get_session)
):
    """
    确认将选中的 Postman 接口持久化导入到指定的机器节点下
    """
    try:
        res = import_postman_to_machine(
            db=session,
            machine_id=machine_id,
            selected_apis=req.selected_apis,
            environment_variables=req.environment_variables,
            postman_base_url=req.postman_base_url,
            sync_env_vars=req.sync_env_vars,
            update_machine_base_url=req.update_machine_base_url,
            conflict_policy=req.conflict_policy,
            cron_interval_minutes=req.cron_interval_minutes
        )
        return {"success": True, "result": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"导入失败: {str(e)}")


@router.post("/api/apis/import-postman/preview")
async def preview_postman_import_generic(
    machine_id: Optional[int] = Form(None),
    file: Optional[UploadFile] = File(None),
    raw_json: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    """
    通用 Postman 文件解析预览（可由前端接口管理页面直接调用）
    """
    machine = session.get(MachineNode, machine_id) if machine_id else None
    base_url = machine.base_url if machine else None

    file_bytes = b""
    filename = ""
    if file:
        file_bytes = await file.read()
        filename = file.filename or ""
    elif raw_json:
        file_bytes = raw_json.encode("utf-8")
        filename = "content.json"
    else:
        raise HTTPException(status_code=400, detail="请上传 Postman 格式文件 (.zip / .json) 或提供 JSON 文本内容")

    try:
        parsed = parse_postman_package(file_bytes, filename, base_url)
        return {
            "success": True,
            "machine": {
                "id": machine.id,
                "name": machine.name,
                "base_url": machine.base_url
            } if machine else None,
            "data": parsed
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Postman 文件解析失败: {str(e)}")


@router.post("/api/apis/import-postman/confirm")
def confirm_postman_import_generic(
    req: PostmanConfirmImportRequest,
    session: Session = Depends(get_session)
):
    """
    通用 Postman 确认导入接口（需指定 machine_id）
    """
    if not req.machine_id:
        raise HTTPException(status_code=400, detail="请选择目标宿主机器节点 (machine_id)")
    return confirm_postman_import_for_machine(req.machine_id, req, session)
