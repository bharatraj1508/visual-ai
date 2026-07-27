"""Console backend — logs the email instead of sending it.

The default in development: no accounts, no network, and the verification link
is printed to the API logs so you can click through end-to-end.
"""
from __future__ import annotations

from app.core.logging import logger
from app.services.email.base import EmailMessage, EmailSender


class ConsoleEmailSender(EmailSender):
    async def send(self, message: EmailMessage) -> None:
        logger.info(
            "[email:console] to=%s subject=%r\n--- text body ---\n%s\n---",
            message.to,
            message.subject,
            message.text,
        )
