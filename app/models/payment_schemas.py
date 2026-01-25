from __future__ import annotations

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class SubscriptionPlan(str, Enum):
<<<<<<< HEAD
    FREE = "free"            # 9 credits (3 requests) per week - ₦0
    STARTER = "starter"      # 120 credits (40 requests) - ₦7,500
    BASIC = "basic"          # 240 credits (80 requests) - ₦12,000
    STUDIO = "studio"        # 450 credits (150 requests) - ₦25,000
=======
    FREE = "free"            # 5 credits - ₦0
    STARTER = "starter"      # 10 credits - ₦3,999.00
    BASIC = "basic"          # 30 credits - ₦7,999.00
    PREMIUM = "premium"      # 50 credits - ₦11,999.00
    PROFESSIONAL = "professional"  # 150 credits - ₦29,999.00
>>>>>>> origin/master


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESSFUL = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CreateSubscriptionRequest(BaseModel):
    plan: SubscriptionPlan
    callback_url: Optional[str] = None


class CreatePaymentRequest(BaseModel):
    amount: int
    callback_url: Optional[str] = None


class InitializePaymentResponse(BaseModel):
    redirect_url: str
    reference: str
    amount: int  # in kobo
    plan: Optional[SubscriptionPlan] = None


class PaymentConfirmRequest(BaseModel):
    reference: str


class PaymentHistoryItem(BaseModel):
    id: str
    plan: Optional[SubscriptionPlan] = None
    amount: int  # in kobo
    credits: int
    status: PaymentStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    is_subscription: bool = False
    reference: Optional[str] = None


class PaymentHistoryResponse(BaseModel):
    payments: List[PaymentHistoryItem]
    total_count: int


class SubscriptionPlanInfo(BaseModel):
    plan: SubscriptionPlan
    credits: int
    price: int
    price_display: str
    description: str
    popular: bool = False


class PricingResponse(BaseModel):
    plans: List[SubscriptionPlanInfo]


class SubscriptionDetails(BaseModel):
    id: str
    plan: SubscriptionPlan
    plan_code: str
    credits: int
    status: SubscriptionStatus
    next_payment_date: Optional[datetime] = None
    created_at: datetime
    last_payment_date: Optional[datetime] = None


class SubscriptionResponse(BaseModel):
    subscription: Optional[SubscriptionDetails] = None


class SubscriptionListResponse(BaseModel):
    subscriptions: List[SubscriptionDetails]
    total_count: int


class CancelSubscriptionRequest(BaseModel):
    subscription_id: str


class CancelSubscriptionResponse(BaseModel):
    success: bool
    message: str
