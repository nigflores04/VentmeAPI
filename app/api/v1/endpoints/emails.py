from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.db.client import get_db
from app.services.email_collection_service import EmailCollectionService
from app.core.auth import get_current_user_required
from app.models.email_schemas import (
    EmailSubscribeRequest,
    EmailSubscribeResponse,
    EmailListResponse
)
from app.models.auth_schemas import UserPublic
from prisma import Prisma
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/emails", tags=["emails"])


class UnsubscribeRequest(BaseModel):
    email: EmailStr


# Public endpoint - no authentication required
@router.post("/subscribe", response_model=EmailSubscribeResponse)
async def subscribe_email(
    subscribe_data: EmailSubscribeRequest,
    db: Prisma = Depends(get_db)
):
    """Collect an email address (public endpoint)"""
    email_service = EmailCollectionService(db)
    
    subscriber = await email_service.subscribe_email(subscribe_data)
    if not subscriber:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to subscribe email"
        )
    
    return EmailSubscribeResponse(
        success=True,
        message="Email successfully added to our list",
    )


@router.post("/unsubscribe")
async def unsubscribe_email(
    unsubscribe_data: UnsubscribeRequest,
    db: Prisma = Depends(get_db)
):
    """Unsubscribe an email address (public endpoint)"""
    email_service = EmailCollectionService(db)
    
    success = await email_service.unsubscribe_email(unsubscribe_data.email)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    return {"success": True, "message": "Email successfully unsubscribed"}


# Admin endpoints - authentication required
@router.get("/subscribers", response_model=EmailListResponse)
async def get_email_subscribers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    current_user: UserPublic = Depends(get_current_user_required),
    db: Prisma = Depends(get_db)
):
    """Get all email subscribers (admin only)"""
    email_service = EmailCollectionService(db)
    return await email_service.get_subscribers(skip=skip, limit=limit, active_only=active_only)


@router.get("/stats")
async def get_email_stats(
    current_user: UserPublic = Depends(get_current_user_required),
    db: Prisma = Depends(get_db)
):
    """Get email collection statistics (admin only)"""
    email_service = EmailCollectionService(db)
    return await email_service.get_subscriber_count()
