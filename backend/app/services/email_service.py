import asyncio
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime

# 可从环境变量或配置文件读取 SMTP 设置
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")          # 发件人邮箱，如: your_name@qq.com
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # 邮箱授权码/密码
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "true").lower() == "true"


def generate_alert_email_html(
    target_name: str,
    target_addr: str,
    failure_reasons: List[str],
    consecutive_failures: int,
    tcp_info: tuple,
    http_info: tuple,
    schema_errors: List[Dict[str, Any]],
    raw_snippet: str = ""
) -> str:
    """生成专业的 HTML 故障告警邮件模板"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reasons_html = "".join([f"<li><b style='color:#e74c3c;'>{r}</b></li>" for r in failure_reasons])
    
    schema_rows = ""
    if schema_errors:
        for err in schema_errors:
            schema_rows += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 8px; font-family: monospace; color: #d63031;">{err.get('field', '$root')}</td>
                <td style="padding: 8px; color: #e17055;">{err.get('validator', '')}</td>
                <td style="padding: 8px; color: #2d3436;">{err.get('message', '')}</td>
            </tr>
            """
    else:
        schema_rows = "<tr><td colspan='3' style='padding:8px; color:#27ae60;'>Schema 结构完全符合预期</td></tr>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>服务健康与结构异常告警</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f7f9; padding: 20px; margin: 0;">
        <div style="max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-top: 5px solid #e74c3c;">
            <div style="padding: 24px 30px; background: #fff;">
                <h2 style="color: #c0392b; margin-top: 0; display: flex; align-items: center; gap: 8px;">
                    🚨 【SchemaPulse】服务健康与结构异常告警
                </h2>
                <p style="color: #7f8c8d; font-size: 14px;">监控引擎在巡检中检测到目标服务发生异常或破坏性结构变更，请及时关注排查。</p>
                
                <table style="width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px;">
                    <tr style="background: #fdf2f2;">
                        <td style="padding: 10px; width: 120px; font-weight: bold; color: #333;">监控目标</td>
                        <td style="padding: 10px; color: #2c3e50;"><b>{target_name}</b> ({target_addr})</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold; color: #333;">检测时间</td>
                        <td style="padding: 10px; color: #555;">{now_str}</td>
                    </tr>
                    <tr style="background: #fdf2f2;">
                        <td style="padding: 10px; font-weight: bold; color: #333;">连续失败</td>
                        <td style="padding: 10px; color: #c0392b; font-weight: bold;">{consecutive_failures} 次</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; font-weight: bold; color: #333;">故障原因</td>
                        <td style="padding: 10px; color: #555;"><ul style="margin:0; padding-left:20px;">{reasons_html}</ul></td>
                    </tr>
                </table>

                <h3 style="color: #2c3e50; margin-top: 25px; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px;">📊 核心网络与协议指标</h3>
                <div style="display: flex; gap: 15px; margin-top: 10px;">
                    <div style="flex: 1; background: #f8f9fa; padding: 12px; border-radius: 6px; border: 1px solid #e9ecef;">
                        <div style="color: #6c757d; font-size: 12px;">TCP 端口连通</div>
                        <div style="font-size: 16px; font-weight: bold; color: {'#27ae60' if tcp_info[0] else '#e74c3c'}; margin-top: 4px;">
                            {'✅ 开放' if tcp_info[0] else '❌ 未连通'}
                            <span style="font-size: 12px; color: #888; font-weight: normal;">({tcp_info[1]}ms)</span>
                        </div>
                    </div>
                    <div style="flex: 1; background: #f8f9fa; padding: 12px; border-radius: 6px; border: 1px solid #e9ecef;">
                        <div style="color: #6c757d; font-size: 12px;">HTTP 状态码</div>
                        <div style="font-size: 16px; font-weight: bold; color: {'#27ae60' if http_info[0] == 200 else '#e74c3c'}; margin-top: 4px;">
                            {http_info[0] or '无响应'}
                            <span style="font-size: 12px; color: #888; font-weight: normal;">({http_info[1]}ms)</span>
                        </div>
                    </div>
                </div>

                <h3 style="color: #2c3e50; margin-top: 25px; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px;">🔍 Schema 结构比对差异</h3>
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px;">
                    <thead>
                        <tr style="background: #edf2f7; text-align: left;">
                            <th style="padding: 8px; width: 25%;">异常字段路径</th>
                            <th style="padding: 8px; width: 25%;">规则类型</th>
                            <th style="padding: 8px;">错误描述</th>
                        </tr>
                    </thead>
                    <tbody>
                        {schema_rows}
                    </tbody>
                </table>

                {f'''
                <h3 style="color: #2c3e50; margin-top: 25px; border-bottom: 2px solid #ecf0f1; padding-bottom: 8px;">📄 现场响应快照 (前 400 字符)</h3>
                <pre style="background: #2d3436; color: #dfe6e9; padding: 12px; border-radius: 6px; font-size: 12px; overflow-x: auto;">{raw_snippet[:400]}</pre>
                ''' if raw_snippet else ''}

                <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #eee; text-align: center; color: #95a5a6; font-size: 12px;">
                    此邮件由 SchemaPulse 智能监控探针系统自动发出，请勿直接回复。
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def generate_recovery_email_html(target_name: str, target_addr: str) -> str:
    """生成故障恢复 HTML 邮件模板"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; background-color: #f4f7f9; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; overflow: hidden; border-top: 5px solid #27ae60; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
            <div style="padding: 24px 30px;">
                <h2 style="color: #27ae60; margin-top: 0;">🟢 【SchemaPulse】服务健康已恢复</h2>
                <p style="color: #555; font-size: 14px;">目标服务已恢复正常运行，TCP 连通、HTTP 状态码及 JSON Schema 断言均已验证通过。</p>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 15px;">
                    <tr style="background: #f0fdf4;">
                        <td style="padding: 10px; width: 100px; font-weight: bold;">监控目标</td>
                        <td style="padding: 10px;"><b>{target_name}</b> ({target_addr})</td>
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
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"\n[邮件模拟输出] 未配置 SMTP 账号信息，已生成邮件 (发送给: {receivers}, 主题: {subject})")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(receivers)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if SMTP_USE_SSL:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)
    else:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        server.starttls()

    try:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, receivers, msg.as_string())
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
