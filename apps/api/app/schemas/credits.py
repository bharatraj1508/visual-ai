"""Credit / billing DTOs.

Note the deliberate asymmetry: PackRead exposes NO currency price (the app shows
credits only), while PurchaseRead does (it's a financial record / receipt).
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BalanceRead(BaseModel):
    available: int
    held: int
    total: int  # available + held


class LedgerEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entry_type: str
    amount: int
    bucket: str
    balance_after: int
    reason: str | None = None
    related_report_id: uuid.UUID | None = None
    related_purchase_id: uuid.UUID | None = None
    expires_at: datetime | None = None
    created_at: datetime


class EstimateResponse(BaseModel):
    cost: int
    balance: int       # available credits
    affordable: bool


class PackRead(BaseModel):
    """Credits-only view for the packs grid — no currency by design."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    base_credits: int
    bonus_credits: int
    total_credits: int
    badge: str | None = None
    sort_order: int


class CheckoutRequest(BaseModel):
    pack_id: uuid.UUID


class CheckoutResponse(BaseModel):
    checkout_url: str


class PurchaseRead(BaseModel):
    """History / receipt record — currency IS shown here (financial record)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    credits_granted: int
    price_minor: int
    currency: str
    status: str
    created_at: datetime


class AdminGrantRequest(BaseModel):
    user_id: uuid.UUID
    amount: int = Field(description="Positive to grant, negative to remove.")
    reason: str = Field(min_length=1, max_length=255)
