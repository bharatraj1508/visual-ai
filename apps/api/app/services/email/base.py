"""Provider-agnostic email interface.

The rest of the app depends only on `EmailSender` + `EmailMessage`, never on a
concrete provider. Swapping Resend for SES/Postmark later means adding one file
and a factory branch — no caller changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    html: str
    text: str


class EmailSender(ABC):
    @abstractmethod
    async def send(self, message: EmailMessage) -> None:
        """Deliver a message. Raise on unrecoverable failure so callers can log
        it; callers decide whether a send failure should surface to the user."""
        raise NotImplementedError
