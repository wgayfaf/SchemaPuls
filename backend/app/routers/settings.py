"""系统设置: SMTP 邮件服务配置 (前端设置页维护, 存储于数据库)"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.models import SmtpConfig
from app.services.email_service import send_email_notification, get_smtp_config

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SmtpConfigPayload(BaseModel):
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: Optional[str] = ""   # 为空表示保留已保存的密码
    smtp_use_ssl: bool = True


class SmtpTestPayload(BaseModel):
    receiver: str


@router.get("/smtp")
def get_smtp_settings(session: Session = Depends(get_session)):
    """读取 SMTP 配置 (密码永不回传, 仅返回是否已设置)"""
    row = session.get(SmtpConfig, 1)
    if row:
        return {
            "smtp_host": row.smtp_host,
            "smtp_port": row.smtp_port,
            "smtp_user": row.smtp_user,
            "smtp_use_ssl": row.smtp_use_ssl,
            "password_set": bool(row.smtp_password),
            "source": "database"
        }
    # 未在页面上配置过: 展示环境变量兜底值
    env_cfg = get_smtp_config()
    return {
        "smtp_host": env_cfg["host"],
        "smtp_port": env_cfg["port"],
        "smtp_user": env_cfg["user"],
        "smtp_use_ssl": env_cfg["use_ssl"],
        "password_set": bool(env_cfg["password"]),
        "source": env_cfg["source"]
    }


@router.put("/smtp")
def update_smtp_settings(payload: SmtpConfigPayload, session: Session = Depends(get_session)):
    """保存 SMTP 配置; 密码留空表示保留原值"""
    row = session.get(SmtpConfig, 1)
    if not row:
        row = SmtpConfig(id=1)
    row.smtp_host = payload.smtp_host.strip() or "smtp.qq.com"
    row.smtp_port = payload.smtp_port
    row.smtp_user = payload.smtp_user.strip()
    if payload.smtp_password:  # 仅在填写了新密码时覆盖
        row.smtp_password = payload.smtp_password
    row.smtp_use_ssl = payload.smtp_use_ssl
    from datetime import datetime
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
    return {"status": "ok", "message": "SMTP 配置已保存"}


@router.post("/smtp/test")
async def test_smtp_settings(payload: SmtpTestPayload):
    """向指定邮箱发送一封测试邮件 (使用当前生效配置)"""
    cfg = get_smtp_config()
    if not cfg["user"] or not cfg["password"]:
        raise HTTPException(status_code=400, detail="请先完整填写并保存 SMTP 账号与授权码")
    if not payload.receiver or "@" not in payload.receiver:
        raise HTTPException(status_code=400, detail="请填写有效的测试收件邮箱")
    subject = "🧪【SchemaPulse】SMTP 配置测试邮件"
    html = f"""
    <div style="font-family: sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
      <h2 style="color: #059669;">✅ SMTP 配置测试成功</h2>
      <p>配置来源: <b>{cfg['source']}</b> | 服务器: {cfg['host']}:{cfg['port']} | 发件人: {cfg['user']}</p>
      <p style="color: #64748b;">收到此邮件说明 SchemaPulse 的机器告警邮件通道已就绪。</p>
    </div>
    """
    await send_email_notification([payload.receiver.strip()], subject, html)
    return {"status": "ok", "message": f"测试邮件已发送至 {payload.receiver}"}
