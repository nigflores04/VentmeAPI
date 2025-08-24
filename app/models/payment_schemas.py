from __future__ import annotations

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class CreditPackage(str, Enum):
    STARTER = "starter"      # 10 credits - $9.99
    BASIC = "basic"          # 25 credits - $19.99
    PREMIUM = "premium"      # 60 credits - $39.99
    PROFESSIONAL = "professional"  # 150 credits - $79.99


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CreatePaymentRequest(BaseModel):
    package: CreditPackage
    return_url: Optional[str] = None


class PaymentIntentResponse(BaseModel):
    payment_intent_id: str
    client_secret: str
    amount: int  # in cents
    credits: int
    package: CreditPackage


class PaymentConfirmRequest(BaseModel):
    payment_intent_id: str


class PaymentHistoryItem(BaseModel):
    id: str
    package: CreditPackage
    amount: int  # in cents
    credits: int
    status: PaymentStatus
    created_at: datetime
    completed_at: Optional[datetime] = None


class PaymentHistoryResponse(BaseModel):
    payments: List[PaymentHistoryItem]
    total_count: int


class CreditPackageInfo(BaseModel):
    package: CreditPackage
    credits: int
    price_cents: int
    price_display: str
    description: str
    popular: bool = False


class PricingResponse(BaseModel):
    packages: List[CreditPackageInfo]
