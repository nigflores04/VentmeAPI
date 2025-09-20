from __future__ import annotations

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Header, Response
import logging
import json

from app.core.auth import get_current_user_required
from app.models.payment_schemas import (
    CreatePaymentRequest, CreateSubscriptionRequest, InitializePaymentResponse, PaymentConfirmRequest,
    PaymentHistoryResponse, PricingResponse
)
from app.services import payment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/pricing", response_model=PricingResponse)
async def get_pricing():
    """Get available credit plans and pricing"""
    return await payment_service.get_pricing()


@router.post("/initialize", response_model=InitializePaymentResponse)
async def initialize_payment(
    request: CreatePaymentRequest,
    current_user: dict = Depends(get_current_user_required),
):
    """Create a payment intent for purchasing credits using Paystack"""
    try:
        payment_response = await payment_service.initialize_payment(
            user_id=current_user["id"],
            request=request
        )
        return payment_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/subscribe", response_model=InitializePaymentResponse)
async def initialize_subscription(
    request: CreateSubscriptionRequest,
    current_user: dict = Depends(get_current_user_required),
):
    """Create a subscription for recurring credit purchases using Paystack"""
    try:
        subscription_response = await payment_service.initialize_subscription(
            user_id=current_user["id"],
            request=request
        )
        return subscription_response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify")
async def verify_payment(
    request: PaymentConfirmRequest,
    current_user: dict = Depends(get_current_user_required),
):
    """Confirm a payment and add credits to user account"""
    try:
        payment_status = await payment_service.verify_payment(request.reference)
        if payment_status == payment_service.PaymentStatus.SUCCESSFUL:
            return {"message": "Payment confirmed successfully", "success": True, "status": payment_status.value}
        elif payment_status == payment_service.PaymentStatus.PENDING:
            return {"message": "Payment is still processing", "success": False, "status": payment_status.value}
        else:
            return {"message": "Payment failed or was cancelled", "success": False, "status": payment_status.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    current_user: dict = Depends(get_current_user_required),
    limit: int = 20,
    offset: int = 0,
):
    """Get payment history for the authenticated user"""
    return await payment_service.get_payment_history(
        user_id=current_user["id"],
        limit=limit,
        offset=offset
    )


@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    paystack_signature: Optional[str] = Header(None, alias="x-paystack-signature"),
):
    """Handle Paystack webhook events"""
    # Paystack sends a signature in the x-paystack-signature header
    # This can be used to verify the webhook is from Paystack
    if not paystack_signature:
        logger.warning("Missing Paystack signature header")
        # Some implementations might want to reject requests without signatures
        # For now, we'll continue processing but log a warning
    
    try:
        # Get the raw payload
        payload_bytes = await request.body()
        
        # Parse the JSON payload
        payload = json.loads(payload_bytes)
        
        # Process the webhook
        success = await payment_service.handle_paystack_webhook(payload)
        
        if success:
            # Paystack expects a 200 response
            return Response(content=json.dumps({"status": "success"}), media_type="application/json")
        else:
            # Log the failure but still return 200 to prevent retries
            logger.error("Webhook processing failed but returning 200 to prevent retries")
            return Response(content=json.dumps({"status": "failure"}), media_type="application/json")
            
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        # Still return 200 to prevent Paystack from retrying
        return Response(content=json.dumps({"status": "error", "message": str(e)}), media_type="application/json")


@router.get("/verify/{reference}")
async def verify_payment_by_reference(reference: str):
    """Verify a payment by reference - useful for handling payment callback"""
    try:
        payment_status = await payment_service.verify_payment(reference)
        if payment_status == payment_service.PaymentStatus.SUCCESSFUL:
            return {"message": "Payment verified successfully", "success": True, "status": payment_status.value}
        elif payment_status == payment_service.PaymentStatus.PENDING:
            return {"message": "Payment is still processing", "success": False, "status": payment_status.value}
        else:
            return {"message": "Payment failed or was cancelled", "success": False, "status": payment_status.value}
    except ValueError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
