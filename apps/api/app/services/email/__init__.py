"""Email service package — exposes a single factory that picks the backend
from settings, so callers just do `get_email_sender().send(msg)`.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.services.email.base import EmailMessage, EmailSender
from app.services.email.console import ConsoleEmailSender
from app.services.email.resend import ResendEmailSender
from app.services.email.smtp import SMTPEmailSender

_BACKENDS = {
    "console": ConsoleEmailSender,
    "smtp": SMTPEmailSender,
    "resend": ResendEmailSender,
}


@lru_cache
def get_email_sender() -> EmailSender:
    provider = settings.EMAIL_PROVIDER.lower()
    try:
        return _BACKENDS[provider]()
    except KeyError:
        raise RuntimeError(
            f"Unknown EMAIL_PROVIDER={settings.EMAIL_PROVIDER!r}; "
            f"expected one of {sorted(_BACKENDS)}."
        )


__all__ = ["EmailMessage", "EmailSender", "get_email_sender"]
