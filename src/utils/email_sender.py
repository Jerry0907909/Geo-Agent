"""邮件发送工具 - 通过 SMTP（QQ 邮箱）发送验证码等邮件"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from src.utils.config import get_config

logger = logging.getLogger(__name__)


class EmailSender:
    """SMTP 邮件发送器"""

    def __init__(self):
        config = get_config()
        smtp_cfg = config.config.get("smtp", {})
        self._host = smtp_cfg.get("host") or ""
        self._port = int(smtp_cfg.get("port", 465))
        self._user = smtp_cfg.get("user") or ""
        self._password = smtp_cfg.get("password") or ""
        self._from = smtp_cfg.get("from") or self._user
        self._enabled = bool(self._host and self._user and self._password)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def send_verification_code(self, to_email: str, code: str) -> bool:
        """发送验证码邮件"""
        subject = "Geo-Agent 邮箱验证码"
        body = f"""<div style="max-width:480px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <h2 style="color:#6366f1">Geo-Agent 邮箱验证</h2>
  <p>你的验证码是：</p>
  <div style="background:#f3f4f6;border-radius:12px;padding:24px;text-align:center;margin:16px 0">
    <span style="font-size:32px;font-weight:700;letter-spacing:6px;color:#1f2937">{code}</span>
  </div>
  <p style="color:#6b7280;font-size:14px">验证码 5 分钟内有效，请勿转发给他人。</p>
  <hr style="border:0;border-top:1px solid #e5e7eb;margin:24px 0">
  <p style="color:#9ca3af;font-size:12px">Geo-Agent 地质文献智能问答系统</p>
</div>"""
        return self._send(to_email, subject, body)

    def _send(self, to_email: str, subject: str, html_body: str) -> bool:
        if not self._enabled:
            logger.warning("SMTP 未配置，跳过邮件发送")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            if self._port == 465:
                with smtplib.SMTP_SSL(self._host, self._port, timeout=10) as server:
                    server.login(self._user, self._password)
                    server.sendmail(self._from, to_email, msg.as_string())
            else:
                with smtplib.SMTP(self._host, self._port, timeout=10) as server:
                    server.starttls()
                    server.login(self._user, self._password)
                    server.sendmail(self._from, to_email, msg.as_string())

            logger.info("验证码邮件已发送到 %s", to_email)
            return True

        except Exception as e:
            logger.error("邮件发送失败: %s", e)
            return False


# 全局单例
_email_sender: Optional[EmailSender] = None


def get_email_sender() -> EmailSender:
    global _email_sender
    if _email_sender is None:
        _email_sender = EmailSender()
    return _email_sender
