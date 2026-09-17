import asyncio
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional

from sqlmodel import Session
from datetime import datetime

from app.database import engine
from app.models import SmtpConfig

# 环境变量作为兜底默认值 (数据库未配置时生效)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")          # 发件人邮箱，如: your_name@qq.com
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # 邮箱授权码/密码
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "true").lower() == "true"


def get_smtp_config() -> Dict[str, Any]:
    """读取生效的 SMTP 配置: 数据库中前端保存的配置优先, 未配置时回退环境变量"""
    with Session(engine) as session:
        row = session.get(SmtpConfig, 1)
        if row and row.smtp_user and row.smtp_password:
            return {
                "host": row.smtp_host,
                "port": row.smtp_port,
                "user": row.smtp_user,
                "password": row.smtp_password,
                "use_ssl": row.smtp_use_ssl,
                "receivers": list(row.alert_receivers or []),
                "source": "database"
            }
    return {
        "host": SMTP_HOST,
        "port": SMTP_PORT,
        "user": SMTP_USER,
        "password": SMTP_PASSWORD,
        "use_ssl": SMTP_USE_SSL,
        "receivers": [],
        "source": "environment"
    }


def generate_machine_offline_email_html(
    machine_name: str,
    host: str,
    port: int,
    error_msg: str,
    consecutive_failures: int,
    suspended_apis_count: int
) -> str:
    """生成机器节点不可达与接口熔断通知 (告警风暴收敛邮件)"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; background-color: #f4f7f9; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; overflow: hidden; border-top: 5px solid #dc2626; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <div style="padding: 24px 30px;">
                <h2 style="color: #dc2626; margin-top: 0;">🚨 【SchemaPulse】机器节点不可达告警</h2>
                <p style="color: #555; font-size: 14px;">该机器节点网络或 TCP 端口连通性探测失败，系统已触发<b>自动熔断保护</b>，暂停对其名下所有接口的轮询请求，以避免产生网络告警风暴。</p>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 15px;">
                    <tr style="background: #fef2f2;">
                        <td style="padding: 10px; width: 110px; font-weight: bold;">故障机器</td>
                        <td style="padding: 10px;"><b>{machine_name}</b> ({host}:{port})</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">探测异常</td>
                        <td style="padding: 10px; color: #dc2626;">{error_msg or 'TCP 端口握手失败 / 连接超时拒绝'}</td>
                    </tr>
                    <tr style="background: #f8fafc;">
                        <td style="padding: 10px; font-weight: bold;">连续失败次数</td>
                        <td style="padding: 10px; color: #dc2626; font-weight: bold;">{consecutive_failures} 次</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">熔断挂起接口</td>
                        <td style="padding: 10px; color: #d97706; font-weight: bold;">已自动熔断暂停 {suspended_apis_count} 个名下接口探活</td>
                    </tr>
                    <tr style="background: #f8fafc;">
                        <td style="padding: 10px; font-weight: bold;">告警时间</td>
                        <td style="padding: 10px; color: #666;">{now_str}</td>
                    </tr>
                </table>
                <div style="margin-top: 25px; padding: 12px; background: #eff6ff; border-radius: 6px; border: 1px solid #bfdbfe; font-size: 12px; color: #1e40af;">
                    ℹ️ 告警收敛提示：在机器恢复前，系统将不再向名下接口重复发送报错通知。
                </div>
            </div>
        </div>
    </body>
    </html>
    """


def generate_machine_recovery_email_html(
    machine_name: str,
    host: str,
    port: int,
    restored_apis_count: int
) -> str:
    """生成机器节点恢复与熔断解除邮件模板"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; background-color: #f4f7f9; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; overflow: hidden; border-top: 5px solid #059669; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <div style="padding: 24px 30px;">
                <h2 style="color: #059669; margin-top: 0;">🟢 【SchemaPulse】机器节点恢复上线</h2>
                <p style="color: #555; font-size: 14px;">该机器节点 TCP 端口与网络已恢复通畅，系统已<b>自动解除熔断状态</b>，全面恢复名下接口探针的正常轮询监控。</p>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 15px;">
                    <tr style="background: #ecfdf5;">
                        <td style="padding: 10px; width: 110px; font-weight: bold;">恢复机器</td>
                        <td style="padding: 10px;"><b>{machine_name}</b> ({host}:{port})</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">恢复状态</td>
                        <td style="padding: 10px; color: #059669; font-weight: bold;">TCP 端口连通正常</td>
                    </tr>
                    <tr style="background: #f8fafc;">
                        <td style="padding: 10px; font-weight: bold;">唤醒接口数量</td>
                        <td style="padding: 10px; color: #0284c7; font-weight: bold;">已恢复 {restored_apis_count} 个业务接口轮询校验</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold;">恢复时间</td>
                        <td style="padding: 10px; color: #666;">{now_str}</td>
                    </tr>
                </table>
            </div>
        </div>
    </body>
    </html>
    """


def _send_smtp_sync(receivers: List[str], subject: str, html_body: str):
    """底层同步 SMTP 发信逻辑"""
    cfg = get_smtp_config()
    if not cfg["user"] or not cfg["password"]:
        print(f"\n[邮件模拟输出] 未配置 SMTP 账号信息，已生成邮件 (发送给: {receivers}, 主题: {subject})")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg["user"]
    msg["To"] = ", ".join(receivers)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if cfg["use_ssl"]:
        server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=10)
    else:
        server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=10)
        server.starttls()

    try:
        server.login(cfg["user"], cfg["password"])
        server.sendmail(cfg["user"], receivers, msg.as_string())
        print(f"[邮件发送成功] 成功发送告警邮件至: {receivers}")
    finally:
        server.quit()


async def send_email_notification(receivers: List[str], subject: str, html_body: str):
    """异步非阻塞邮件发送入口"""
    if not receivers:
        return
    try:
        # 使用线程池发送邮件，避免阻塞 asyncio 调度事件循环
        await asyncio.to_thread(_send_smtp_sync, receivers, subject, html_body)
    except Exception as e:
        print(f"[邮件发送异常] 目标: {receivers}, 错误: {e}")
