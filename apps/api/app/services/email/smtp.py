"""SMTP backend — works with Mailpit (localhost:1025) for dev and Gmail
(smtp.gmail.com:587 + STARTTLS, or :465 + SSL) for real sending.

smtplib is blocking, so the actual send runs in a worker thread to avoid
stalling the event loop. Gmail requires an **App Password** (not the account
password) and rewrites the visible From to the authenticated address.
"""
from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage as MIMEMessage

from app.core.config import settings
from app.services.email.base import EmailMessage, EmailSender


class SMTPEmailSender(EmailSender):
    def _build_mime(self, message: EmailMessage) -> MIMEMessage:
        mime = MIMEMessage()
        mime["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
        mime["To"] = message.to
        mime["Subject"] = message.subject
        mime.set_content(message.text)
        mime.add_alternative(message.html, subtype="html")
        return mime

    def _open(self) -> smtplib.SMTP:
        # Port 465 = implicit SSL; anything else (587) = plain connect then
        # upgrade with STARTTLS when SMTP_USE_TLS is on (Gmail needs this).
        if settings.SMTP_PORT == 465:
            return smtplib.SMTP_SSL(
                settings.SMTP_HOST, settings.SMTP_PORT, timeout=15
            )
        smtp = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
        smtp.ehlo()
        if settings.SMTP_USE_TLS:
            smtp.starttls()
            smtp.ehlo()
        return smtp

    def _send_sync(self, message: EmailMessage) -> None:
        with self._open() as smtp:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                smtp.login(
                    settings.SMTP_USER,
                    settings.SMTP_PASSWORD.get_secret_value(),
                )
            smtp.send_message(self._build_mime(message))

    async def send(self, message: EmailMessage) -> None:
        await asyncio.to_thread(self._send_sync, message)
