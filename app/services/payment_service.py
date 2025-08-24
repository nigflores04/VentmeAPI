# from __future__ import annotations

# import os
# import uuid
# import logging
# from typing import Dict, List, Optional
# from datetime import datetime

# # import stripe
# from app.core.config import settings
# from app.db import client as db_client
# from app.models.payment_schemas import (
#     CreditPackage, PaymentStatus, CreatePaymentRequest, PaymentIntentResponse,
#     PaymentHistoryItem, PaymentHistoryResponse, CreditPackageInfo, PricingResponse
# )

# logger = logging.getLogger(__name__)

# # Configure Stripe
# stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# # Credit package pricing configuration
# CREDIT_PACKAGES: Dict[CreditPackage, Dict] = {
#     CreditPackage.STARTER: {
#         "credits": 10,
#         "price_cents": 999,  # $9.99
#         "description": "Perfect for trying out our AI remodeling service",
#         "popular": False
#     },
#     CreditPackage.BASIC: {
#         "credits": 30,
#         "price_cents": 1999,  # $19.99
#         "description": "Great for small projects and regular use",
#         "popular": True
#     },
#     CreditPackage.PREMIUM: {
#         "credits": 50,
#         "price_cents": 2999,  # $29.99
#         "description": "Best value for frequent users and professionals",
#         "popular": False
#     },
#     # CreditPackage.PROFESSIONAL: {
#     #     "credits": 150,
#     #     "price_cents": 7999,  # $79.99
#     #     "description": "For heavy users and design professionals",
#     #     "popular": False
#     # }
# }


# async def get_pricing() -> PricingResponse:
#     """Get all available credit packages with pricing"""
#     packages = []
#     for package, config in CREDIT_PACKAGES.items():
#         packages.append(CreditPackageInfo(
#             package=package,
#             credits=config["credits"],
#             price_cents=config["price_cents"],
#             price_display=f"${config['price_cents'] / 100:.2f}",
#             description=config["description"],
#             popular=config["popular"]
#         ))
    
#     return PricingResponse(packages=packages)


# async def create_payment_intent(user_id: str, request: CreatePaymentRequest) -> PaymentIntentResponse:
#     """Create a Stripe payment intent for credit purchase"""
#     if not stripe.api_key:
#         raise ValueError("Stripe not configured")
    
#     if db_client.prisma is None:
#         await db_client.connect()
    
#     # Get package configuration
#     if request.package not in CREDIT_PACKAGES:
#         raise ValueError(f"Invalid package: {request.package}")
    
#     config = CREDIT_PACKAGES[request.package]
#     amount = config["price_cents"]
#     credits = config["credits"]
    
#     try:
#         # Create Stripe payment intent
#         intent = stripe.PaymentIntent.create(
#             amount=amount,
#             currency="usd",
#             metadata={
#                 "user_id": user_id,
#                 "package": request.package.value,
#                 "credits": str(credits)
#             }
#         )
        
#         # Create payment record in database
#         payment = await db_client.prisma.payment.create(  # type: ignore
#             data={
#                 "id": str(uuid.uuid4()),
#                 "userId": user_id,
#                 "stripePaymentId": intent.id,
#                 "package": request.package.value,
#                 "amount": amount,
#                 "credits": credits,
#                 "status": PaymentStatus.PENDING.value,
#             }
#         )
        
#         logger.info("Created payment intent %s for user %s, package %s", intent.id, user_id, request.package.value)
        
#         return PaymentIntentResponse(
#             payment_intent_id=intent.id,
#             client_secret=intent.client_secret,
#             amount=amount,
#             credits=credits,
#             package=request.package
#         )
        
#     except stripe.error.StripeError as e:
#         logger.error("Stripe error creating payment intent: %s", str(e))
#         raise ValueError(f"Payment processing error: {str(e)}")


# async def confirm_payment(payment_intent_id: str) -> bool:
#     """Confirm payment and add credits to user account"""
#     if not stripe.api_key:
#         raise ValueError("Stripe not configured")
    
#     try:
#         # Retrieve payment intent from Stripe
#         intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
#         if intent.status != "succeeded":
#             logger.warning("Payment intent %s not succeeded, status: %s", payment_intent_id, intent.status)
#             return False
        
#         # Find payment record
#         payment = await db_client.prisma.payment.find_unique(  # type: ignore
#             where={"stripePaymentId": payment_intent_id}
#         )
        
#         if not payment:
#             logger.error("Payment record not found for intent %s", payment_intent_id)
#             return False
        
#         if payment.status == PaymentStatus.COMPLETED.value:  # type: ignore[attr-defined]
#             logger.info("Payment %s already completed", payment_intent_id)
#             return True
        
#         # Update payment status and add credits to user
#         await db_client.prisma.payment.update(  # type: ignore
#             where={"stripePaymentId": payment_intent_id},
#             data={
#                 "status": PaymentStatus.COMPLETED.value,
#                 "completedAt": datetime.utcnow()
#             }
#         )
        
#         # Add credits to user account
#         await db_client.prisma.user.update(  # type: ignore
#             where={"id": payment.userId},  # type: ignore[attr-defined]
#             data={"credits": {"increment": payment.credits}}  # type: ignore[attr-defined]
#         )
        
#         logger.info("Payment %s confirmed, added %d credits to user %s", 
#                    payment_intent_id, payment.credits, payment.userId)  # type: ignore[attr-defined]
        
#         return True
        
#     except stripe.error.StripeError as e:
#         logger.error("Stripe error confirming payment: %s", str(e))
#         return False


# async def get_payment_history(user_id: str, limit: int = 20, offset: int = 0) -> PaymentHistoryResponse:
#     """Get payment history for a user"""
#     if db_client.prisma is None:
#         await db_client.connect()
    
#     # Get payments with pagination
#     payments = await db_client.prisma.payment.find_many(  # type: ignore
#         where={"userId": user_id},
#         take=limit,
#         skip=offset,
#     )
    
#     # Get total count
#     total_count = await db_client.prisma.payment.count(where={"userId": user_id})  # type: ignore
    
#     # Convert to response format
#     payment_items = []
#     for payment in payments:
#         payment_items.append(PaymentHistoryItem(
#             id=payment.id,
#             package=CreditPackage(payment.package),  # type: ignore[attr-defined]
#             amount=payment.amount,  # type: ignore[attr-defined]
#             credits=payment.credits,  # type: ignore[attr-defined]
#             status=PaymentStatus(payment.status),  # type: ignore[attr-defined]
#             created_at=payment.createdAt,  # type: ignore[attr-defined]
#             completed_at=payment.completedAt  # type: ignore[attr-defined]
#         ))
    
#     return PaymentHistoryResponse(
#         payments=payment_items,
#         total_count=total_count
#     )


# async def handle_stripe_webhook(payload: bytes, signature: str) -> bool:
#     """Handle Stripe webhook events"""
#     webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
#     if not webhook_secret:
#         logger.error("Stripe webhook secret not configured")
#         return False
    
#     try:
#         event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
        
#         if event["type"] == "payment_intent.succeeded":
#             payment_intent = event["data"]["object"]
#             await confirm_payment(payment_intent["id"])
            
#         elif event["type"] == "payment_intent.payment_failed":
#             payment_intent = event["data"]["object"]
#             await _handle_payment_failure(payment_intent["id"])
            
#         return True
        
#     except ValueError as e:
#         logger.error("Invalid webhook payload: %s", str(e))
#         return False
#     except stripe.error.SignatureVerificationError as e:
#         logger.error("Invalid webhook signature: %s", str(e))
#         return False


# async def _handle_payment_failure(payment_intent_id: str):
#     """Handle failed payment"""
#     if db_client.prisma is None:
#         await db_client.connect()
    
#     await db_client.prisma.payment.update(  # type: ignore
#         where={"stripePaymentId": payment_intent_id},
#         data={"status": PaymentStatus.FAILED.value}
#     )
    
#     logger.info("Marked payment %s as failed", payment_intent_id)
