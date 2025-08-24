from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Header
import logging

from app.core.auth import get_current_user_required
from app.models.payment_schemas import (
    CreatePaymentRequest, PaymentIntentResponse, PaymentConfirmRequest,
    PaymentHistoryResponse, PricingResponse
)
from app.services import payment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/pricing", response_model=PricingResponse)
async def get_pricing():
    """Get available credit packages and pricing"""
    # return await payment_service.get_pricing()


@router.post("/create-intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    request: CreatePaymentRequest,
    current_user: dict = Depends(get_current_user_required),
):
    """Create a payment intent for purchasing credits"""
    # try:
    #     return await payment_service.create_payment_intent(
    #         user_id=current_user["id"],
    #         request=request
    #     )
    # except ValueError as e:
    #     raise HTTPException(status_code=400, detail=str(e))


@router.post("/confirm")
async def confirm_payment(
    request: PaymentConfirmRequest,
    current_user: dict = Depends(get_current_user_required),
):
    """Confirm a payment and add credits to user account"""
    # try:
    #     success = await payment_service.confirm_payment(request.payment_intent_id)
    #     if success:
    #         return {"message": "Payment confirmed successfully", "success": True}
    #     else:
    #         raise HTTPException(status_code=400, detail="Payment confirmation failed")
    # except ValueError as e:
    #     raise HTTPException(status_code=400, detail=str(e))


@router.get("/history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    current_user: dict = Depends(get_current_user_required),
    limit: int = 20,
    offset: int = 0,
):
    """Get payment history for the authenticated user"""
    # return await payment_service.get_payment_history(
    #     user_id=current_user["id"],
    #     limit=limit,
    #     offset=offset
    # )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
):
    """Handle Stripe webhook events"""
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    
    try:
        payload = await request.body()
        # success = await payment_service.handle_stripe_webhook(payload, stripe_signature)
        
        # if success:
        #     return {"status": "success"}
        # else:
        #     raise HTTPException(status_code=400, detail="Webhook processing failed")
            
    except Exception as e:
        logger.error("Webhook error: %s", str(e))
        raise HTTPException(status_code=400, detail="Webhook processing error")
