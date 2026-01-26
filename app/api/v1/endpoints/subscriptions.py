from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import get_current_user_required
from app.models.payment_schemas import (
    SubscriptionResponse,
    SubscriptionListResponse,
    CancelSubscriptionRequest,
    CancelSubscriptionResponse
)
from app.services import subscription_service


router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/", response_model=SubscriptionListResponse)
async def list_subscriptions(
    current_user: dict = Depends(get_current_user_required)
):
    """List all subscriptions for the current user"""
    subscriptions = await subscription_service.get_user_subscriptions(current_user["id"])
    return SubscriptionListResponse(
        subscriptions=subscriptions,
        total_count=len(subscriptions)
    )


@router.get("/active", response_model=SubscriptionResponse)
async def get_active_subscription(
    current_user: dict = Depends(get_current_user_required)
):
    """Get the active subscription for the current user"""
    subscription = await subscription_service.get_active_subscription(current_user["id"])
    return SubscriptionResponse(subscription=subscription)


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    current_user: dict = Depends(get_current_user_required)
):
    """Get details for a specific subscription"""
    subscription = await subscription_service.get_subscription_details(subscription_id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Check if the subscription belongs to the current user
    # This requires an additional database query, but ensures security
    subscriptions = await subscription_service.get_user_subscriptions(current_user["id"])
    if subscription.id not in [s.id for s in subscriptions]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this subscription"
        )
    
    return SubscriptionResponse(subscription=subscription)


@router.post("/cancel", response_model=CancelSubscriptionResponse)
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    current_user: dict = Depends(get_current_user_required)
):
    """Cancel a subscription"""
    # Check if the subscription belongs to the current user
    subscriptions = await subscription_service.get_user_subscriptions(current_user["id"])
    if request.subscription_id not in [s.id for s in subscriptions]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to cancel this subscription"
        )
    
    success = await subscription_service.cancel_subscription(request.subscription_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to cancel subscription"
        )
    
    return CancelSubscriptionResponse(
        success=True,
        message="Subscription cancelled successfully"
    )
