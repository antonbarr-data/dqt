"""Email notifier -- sends HTML + plain-text digests via SMTP.

Configure via env vars:
  SMTP_HOST   (default: localhost)
  SMTP_PORT   (default: 587)
  SMTP_USER   (optional -- enables STARTTLS + login)
  SMTP_PASS   (optional)
  SMTP_FROM   (default: dqt@localhost)
"""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailNotifier:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        from_addr: str | None = None,
    ) -> None:
        self.host = host or os.environ.get("SMTP_HOST", "localhost")
        self.port = port or int(os.environ.get("SMTP_PORT", "587"))
        self.username = username or os.environ.get("SMTP_USER", "")
        self.password = password or os.environ.get("SMTP_PASS", "")
        self.from_addr = from_addr or os.environ.get("SMTP_FROM", "dqt@localhost")

    def send(self, to_addr: str, subject: str, html: str, plain: str) -> bool:
        """Send HTML + plain-text email. Returns True on success."""
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = to_addr
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                if self.username and self.password:
                    server.starttls()
                    server.login(self.username, self.password)
                server.sendmail(self.from_addr, [to_addr], msg.as_string())
            return True
        except Exception:
            return False
