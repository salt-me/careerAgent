"""Optional SMTP delivery for grounded subscription digests.

Without SMTP configuration this module only records a preview-only delivery;
it never claims that an email has been sent.
"""

from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any

from .repository import JobRepository
from .subscription_matching import subscription_preview
from .workspace import CareerWorkspace


@dataclass(frozen=True)
class SmtpSettings:
    host: str | None
    port: int
    username: str | None
    password: str | None
    sender: str | None
    use_tls: bool

    @classmethod
    def from_env(cls) -> "SmtpSettings":
        return cls(
            host=os.getenv("CAREER_AGENT_SMTP_HOST") or None,
            port=int(os.getenv("CAREER_AGENT_SMTP_PORT", "587")),
            username=os.getenv("CAREER_AGENT_SMTP_USERNAME") or None,
            password=os.getenv("CAREER_AGENT_SMTP_PASSWORD") or None,
            sender=os.getenv("CAREER_AGENT_SMTP_FROM") or None,
            use_tls=os.getenv("CAREER_AGENT_SMTP_USE_TLS", "true").casefold() in {"1", "true", "yes", "on"},
        )

    @property
    def configured(self) -> bool:
        return bool(self.host and self.sender)


class SubscriptionNotifier:
    def __init__(self, workspace: CareerWorkspace, repository: JobRepository, settings: SmtpSettings | None = None) -> None:
        self.workspace = workspace
        self.repository = repository
        self.settings = settings or SmtpSettings.from_env()

    @staticmethod
    def _message(subscription: dict[str, Any], preview: dict[str, Any]) -> tuple[str, str]:
        subject = f"CareerAgent: {subscription['name']} \u65b0\u5c97\u4f4d\u6458\u8981"
        lines = [f"\u5339\u914d\u5c97\u4f4d {preview['matched_count']} \u4e2a\uff0c\u6700\u8fd1\u7a97\u53e3\u5185\u65b0\u589e/\u66f4\u65b0 {preview['fresh_count']} \u4e2a\u3002", ""]
        for item in preview["items"][:10]:
            lines.append(f"- {item['company']} | {item['title']} | {item['location']}")
            lines.append(f"  {item['source_url']}")
        lines.append("")
        lines.append("\u8bf7\u4ee5\u5b98\u65b9\u9875\u9762\u7684\u72b6\u6001\u548c\u622a\u6b62\u65f6\u95f4\u4e3a\u51c6\u3002")
        return subject, "\n".join(lines)

    def deliver(self, subscription: dict[str, Any], *, profile_key: str, recipient: str | None = None) -> dict[str, Any]:
        profile = self.workspace.profile(profile_key)
        recipient = (recipient or profile.get("email") or "").strip()
        preview = subscription_preview(self.repository, subscription)
        subject, body = self._message(subscription, preview)
        if not recipient:
            status, detail = "skipped", "No profile email configured; generated preview only."
        elif not self.settings.configured:
            status, detail = "preview_only", "SMTP is not configured; no message was sent."
        else:
            message = EmailMessage()
            message["Subject"] = subject
            message["From"] = self.settings.sender
            message["To"] = recipient
            message.set_content(body)
            try:
                with smtplib.SMTP(self.settings.host, self.settings.port, timeout=20) as client:
                    if self.settings.use_tls:
                        client.starttls()
                    if self.settings.username:
                        client.login(self.settings.username, self.settings.password or "")
                    client.send_message(message)
                status, detail = "sent", "SMTP accepted the digest."
            except (OSError, smtplib.SMTPException) as error:
                status, detail = "failed", f"{type(error).__name__}: {error}"
        delivery = self.workspace.record_subscription_delivery(
            profile_key=profile_key,
            subscription_id=int(subscription["id"]),
            recipient=recipient or None,
            status=status,
            matched_count=int(preview["matched_count"]),
            detail=detail,
        )
        return {"delivery": delivery, "preview": preview, "subject": subject, "configured": self.settings.configured}

    def dispatch_all(self) -> list[dict[str, Any]]:
        results = []
        for item in self.workspace.active_subscription_targets():
            results.append(self.deliver(item["subscription"], profile_key=item["profile_key"], recipient=item.get("email")))
        return results