from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class EmailSubscribeRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(None, max_length=100)
    source: Optional[str] = Field(None, description="Source of subscription (e.g., 'website', 'landing_page')")


class EmailSubscriberPublic(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str]
    source: Optional[str]
    isActive: bool
    createdAt: datetime


class EmailSubscribeResponse(BaseModel):
    success: bool
    message: str
    subscriber: Optional[EmailSubscriberPublic] = None


class EmailListResponse(BaseModel):
    total: int
    subscribers: list[EmailSubscriberPublic]
