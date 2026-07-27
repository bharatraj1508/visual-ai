"""Resend backend — production sending via the Resend HTTP API.

Uses httpx directly rather than the Resend SDK to avoid an extra dependency;
the API surface we need is a single authenticated POST.
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.services.email.base import EmailMessage, EmailSender

_RESEND_ENDPOINT = "https://api.resend.com/emails"


class ResendEmailSender(EmailSender):
    def __init__(self) -> None:
        if settings.RESEND_API_KEY is None:
            raise RuntimeError(
                "EMAIL_PROVIDER=resend but RESEND_API_KEY is not set."
            )
        self._api_key = settings.RESEND_API_KEY.get_secret_value()

    async def send(self, message: EmailMessage) -> None:
        payload = {
            "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
            "to": [message.to],
            "subject": message.subject,
            "html": message.html,
            "text": message.text,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                _RESEND_ENDPOINT,
                json=payload,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        # Surface Resend's own error message (e.g. "domain is not verified")
        # rather than a bare status code — a naked 403 is undebuggable.
        if resp.is_error:
            raise RuntimeError(
                f"Resend API {resp.status_code} for from={settings.EMAIL_FROM!r} "
                f"to={message.to!r}: {resp.text}"
            )
