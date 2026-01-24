from __future__ import annotations

import os
import uuid
import logging
import time
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import paystack
from paystack.api import Transaction, Customer
from app.core.config import settings
from app.db import client as db_client
from app.core.payment_config import SUBSCRIPTION_PLANS
from app.models.payment_schemas import (
    SubscriptionPlan, PaymentStatus, CreatePaymentRequest, InitializePaymentResponse,
    PaymentHistoryItem, PaymentHistoryResponse, SubscriptionPlanInfo, PricingResponse, CreateSubscriptionRequest
)
from pprint import pprint

logger = logging.getLogger(__name__)

# Configure Paystack
paystack.api_key = settings.PAYSTACK_SECRET_KEY


async def get_pricing() -> PricingResponse:
    """Get all available credit plans with pricing"""
    plans = []
    for plan, config in SUBSCRIPTION_PLANS.items():
        # Format with Naira symbol and thousands separator
        formatted_price = f"₦{config['price'] / 100:,.2f}"
        plans.append(SubscriptionPlanInfo(
            plan=plan,
            credits=config["credits"],
            price=config["price"],
            price_display=formatted_price,
            description=config["description"],
            popular=config["popular"]
        ))
    
    return PricingResponse(plans=plans)


async def initialize_payment(user_id: str, request: CreatePaymentRequest) -> InitializePaymentResponse:
    """Create a Paystack payment intent for credit purchase"""
    if not settings.PAYSTACK_SECRET_KEY:
        raise ValueError("Paystack not configured")
    
    amount = request.amount # Paystack amount is in kobo (smallest currency unit)
    credits = request.amount/100
    
    # Get user information to create/update customer
    user = await db_client.prisma.user.find_unique(  # type: ignore
        where={"id": user_id}
    )
    
    if not user:
        raise ValueError(f"User not found: {user_id}")
    
    try:
        # Generate a unique reference for this transaction
        reference = f"{user_id}-{uuid.uuid4().hex[:8]}"

        transaction_data = paystack.Transaction.initialize(
            email=user.email,  # type: ignore[attr-defined]
            amount=amount,
            currency="NGN",  # Nigerian Naira
            reference=reference,
            callback_url=request.callback_url,
            metadata={
                "user_id": user_id,
                "credits": str(credits)
            }
        )

        # print(transaction_data)


        await db_client.prisma.payment.create( 
            data={
                "id": str(uuid.uuid4()),
                "userId": user_id,
                "payment_reference": reference, 
                # "plan": request.plan.value,
                "amount": amount,
                "credits": credits,
                "status": PaymentStatus.PENDING.value,
                "description": "Purchase credit"
            }
        )
        
        logger.info("Initialized payment %s for user %s, credits %s", reference, user_id, credits)

        return InitializePaymentResponse(
            redirect_url=transaction_data.data["authorization_url"],
            reference=reference,
            amount=amount
        )
    except Exception as e:
        logger.error("Paystack error creating payment: %s", str(e))
        raise ValueError(f"Payment processing error: {str(e)}")


async def initialize_subscription(request: CreateSubscriptionRequest, user_id: str) -> InitializePaymentResponse:
    """Initialize a subscription payment with Paystack"""
    if not settings.PAYSTACK_SECRET_KEY:
        raise ValueError("Paystack not configured")
    
    # Get plan details
    if request.plan.value not in SUBSCRIPTION_PLANS:
        raise ValueError(f"Invalid plan: {request.plan.value}")
    
    plan_config = SUBSCRIPTION_PLANS[request.plan.value]
    amount = plan_config["price"]  # Amount in kobo (smallest currency unit)
    credits = plan_config["credits"]
    
    # Get user details
    user = await db_client.prisma.user.find_first(
        where={"id": user_id}
    )
    
    if not user:
        raise ValueError(f"User not found: {user_id}")
    
    # Check for existing active subscription
    # active_payments = await db_client.prisma.payment.find_many(
    #     where={
    #         "userId": user_id,
    #         "isSubscription": True,
    #         "status": PaymentStatus.SUCCESSFUL.value,
    #         "completedAt": {
    #             "gte": datetime.now().replace(day=1) # Current month
    #         }
    #     }
    # )
    
    # if active_payments:
    #     logger.warning(f"User {user_id} already has an active subscription")
    #     raise ValueError("You already have an active subscription. Please wait until your current subscription expires before subscribing again.")
    
    try:
        # Generate a unique reference for this transaction
        reference = f"{user_id}-{uuid.uuid4().hex[:8]}"
        
        # Step 1: Find the existing plan in Paystack
        plan_name = f"{request.plan.value.capitalize()} Plan"
        paystack_plan_code = None
        
        try:
            # Get all plans from Paystack
            logger.info(f"Looking for existing plan: {plan_name}")
            plans_response = paystack.Plan.list()
            
            if not plans_response or not hasattr(plans_response, 'data'):
                logger.error("Invalid response from Paystack Plan.list: %s", str(plans_response))
                raise ValueError("Could not retrieve plans from Paystack")
            
            # Log number of plans found
            logger.info(f"Found {len(plans_response.data)} plans in Paystack")
            
            # More flexible plan matching - check for exact name match first
            for plan in plans_response.data:
                plan_data = plan if isinstance(plan, dict) else plan.__dict__
                
                # Try to match by name first (exact match)
                if plan_data.get("name") == plan_name:
                    paystack_plan_code = plan_data.get("plan_code")
                    logger.info(f"Found exact plan match: {plan_name}, code: {paystack_plan_code}")
                    break
            
            # If no exact match, try partial match
            if not paystack_plan_code:
                for plan in plans_response.data:
                    plan_data = plan if isinstance(plan, dict) else plan.__dict__
                    
                    # Try to match by name (partial match) and amount
                    plan_name_lower = plan_name.lower()
                    db_name = str(plan_data.get("name", "")).lower()
                    db_amount = plan_data.get("amount")
                    
                    # Check if plan name contains our plan name OR if amounts match
                    if (plan_name_lower in db_name) or (db_amount and int(db_amount) == amount):
                        paystack_plan_code = plan_data.get("plan_code")
                        logger.info(f"Found plan by partial match: {plan_data.get('name')}, amount: {db_amount}, code: {paystack_plan_code}")
                        break
            
            if not paystack_plan_code:
                logger.error(f"Could not find plan: {plan_name} with amount {amount}")
                raise ValueError(f"Plan not found: {plan_name}. Please ensure the plan exists in Paystack.")
                
        except Exception as e:
            logger.error(f"Error finding plan: {str(e)}")
            raise ValueError(f"Could not find plan: {str(e)}")
        
        # Step 2: Initialize transaction with subscription using the found plan
        logger.info(f"Initializing transaction with plan_code: {paystack_plan_code}")
        
        # For subscriptions, we need to use the plan parameter
        transaction_params = {
            "email": user.email,
            "amount": str(int(amount)),  # Add the required amount parameter
            "reference": reference,
            "callback_url": request.callback_url,
            "metadata": {
                "user_id": user_id,
                "plan": request.plan.value,
                "credits": str(credits),
                "is_subscription": "true",
                "plan_code": paystack_plan_code  # Store the plan code in metadata
            }
        }
        
        # Add plan code to parameters
        if paystack_plan_code:
            transaction_params["plan"] = str(paystack_plan_code).strip()
            logger.info(f"Using plan_code for subscription: '{transaction_params['plan']}'")
        
        # Log the full parameters being sent to Paystack
        logger.info(f"Sending transaction parameters to Paystack: {transaction_params}")
        
        try:
            # Initialize transaction with plan
            transaction_data = paystack.Transaction.initialize(**transaction_params)
            logger.info(f"Transaction initialized successfully: {transaction_data.data}")
        except Exception as tx_error:
            logger.error(f"Transaction initialization failed: {str(tx_error)}")
            raise ValueError(f"Failed to initialize transaction: {str(tx_error)}")
        
        # Create payment record in database
        await db_client.prisma.payment.create(
            data={
                "id": str(uuid.uuid4()),
                "userId": user_id,
                "payment_reference": reference,
                "plan": request.plan.value,
                "amount": amount,
                "credits": credits,
                "status": PaymentStatus.PENDING.value,
                "description": f"Subscription to {plan_name}",
                "isSubscription": True
            }
        )
        
        logger.info("Initialized subscription payment %s for user %s, plan %s", 
                   reference, user_id, request.plan.value)
        
        return InitializePaymentResponse(
            redirect_url=transaction_data.data["authorization_url"],
            reference=reference,
            amount=amount,
            plan=request.plan.value
        )
    except Exception as e:
        logger.error("Paystack error creating subscription: %s", str(e))
        raise ValueError(f"Subscription processing error: {str(e)}")


async def verify_payment(payment_reference: str) -> PaymentStatus:
    """Verify payment and add credits to user account"""
    if not settings.PAYSTACK_SECRET_KEY:
        raise ValueError("Paystack not configured")
    
    try:
        transaction_data = paystack.Transaction.verify(reference=payment_reference)
        
        # Find payment record
        payment = await db_client.prisma.payment.find_unique(
            where={"payment_reference": payment_reference}  
        )
        
        if not payment:
            logger.error("Payment record not found for reference %s", payment_reference)
            return PaymentStatus.FAILED
        
        # If payment is already processed, return its status
        if payment.status in [PaymentStatus.SUCCESSFUL.value, PaymentStatus.FAILED.value]:
            logger.info("Payment %s already processed with status %s", payment_reference, payment.status)
            return PaymentStatus(payment.status)
        
        # Get transaction status from Paystack
        transaction_status = transaction_data.data["status"]
        payment_status = PaymentStatus.PROCESSING
        
        # Map Paystack status to our PaymentStatus enum
        if transaction_status == "success":
            payment_status = PaymentStatus.SUCCESSFUL
        elif transaction_status in ["failed", "abandoned", "reversed"]:
            payment_status = PaymentStatus.FAILED
        elif transaction_status == "pending":
            payment_status = PaymentStatus.PENDING
        
        # Update payment status in database
        await db_client.prisma.payment.update( 
            where={"payment_reference": payment_reference},
            data={
                "status": payment_status.value,
                "completedAt": datetime.now() if payment_status in [PaymentStatus.SUCCESSFUL, PaymentStatus.FAILED] else None
            }
        )
        
        # Handle subscription status tracking if this is a subscription payment
        if payment.isSubscription and payment_status == PaymentStatus.SUCCESSFUL:
            # Mark the subscription as active
            await db_client.prisma.payment.update(
                where={"payment_reference": payment_reference},
                data={
                    "status": PaymentStatus.SUCCESSFUL.value,
                    "description": f"Active subscription to {payment.plan} plan"
                }
            )
            
            logger.info(f"Activated subscription for user {payment.userId}, plan {payment.plan}")
        
        # Add credits to user account only if payment was successful
        if payment_status == PaymentStatus.SUCCESSFUL:
            await db_client.prisma.user.update( 
                where={"id": payment.userId}, 
                data={"credits": {"increment": payment.credits}} 
            )
            logger.info("Payment %s confirmed, added %d credits to user %s", 
                       payment_reference, payment.credits, payment.userId)
        else:
            logger.warning("Payment %s not successful, status: %s", payment_reference, payment_status.value)
        
        return payment_status
        
    except Exception as e:
        logger.error("Payment error confirming payment: %s", str(e))
        # Try to update payment status to failed if there was an error
        try:
            await db_client.prisma.payment.update(
                where={"payment_reference": payment_reference},
                data={
                    "status": PaymentStatus.FAILED.value,
                    "completedAt": datetime.now()
                }
            )
        except Exception as update_error:
            logger.error("Failed to update payment status: %s", str(update_error))
            
        raise ValueError(f"Payment verification error: {str(e)}")



async def get_payment_history(user_id: str, limit: int = 20, offset: int = 0) -> PaymentHistoryResponse:
    """Get payment history for a user"""
    if db_client.prisma is None:
        await db_client.connect()
    
    # Get payments with pagination
    payments = await db_client.prisma.payment.find_many(  # type: ignore
        where={"userId": user_id},
        take=limit,
        skip=offset,
    )
    
    # Get total count
    total_count = await db_client.prisma.payment.count(where={"userId": user_id})  # type: ignore
    
    # Convert to response format
    payment_items = []
    for payment in payments:
        payment_items.append(PaymentHistoryItem(
            id=payment.id,
            plan=SubscriptionPlan(payment.plan) if payment.plan else None,
            amount=payment.amount,
            credits=payment.credits,
            status=PaymentStatus(payment.status),
            created_at=payment.createdAt,
            completed_at=payment.completedAt,
            is_subscription=payment.isSubscription,
            reference=payment.payment_reference
        ))
    
    return PaymentHistoryResponse(
        payments=payment_items,
        total_count=total_count
    )


async def handle_paystack_webhook(payload: dict) -> bool:
    """Handle Paystack webhook events"""
    if not settings.PAYSTACK_WEBHOOK_SECRET:
        logger.error("Paystack webhook secret not configured")
        return False
    
    try:
        # Paystack webhooks don't require signature verification like paystack
        # Instead, you should validate the IP address or use a secret in the URL
        # For this example, we'll assume the webhook is properly secured
        
        event_type = payload.get("event")
        data = payload.get("data", {})
        
        if event_type == "charge.success" or event_type == "charge.failed":
            # Process any payment event with verify_payment
            # Our verify_payment function now handles both success and failure cases
            reference = data.get("reference")
            if reference:
                try:
                    payment_status = await verify_payment(reference)
                    logger.info("Webhook processed payment %s with status: %s", reference, payment_status.value)
                except Exception as e:
                    logger.error("Error processing webhook payment %s: %s", reference, str(e))
            
        return True
        
    except ValueError as e:
        logger.error("Invalid webhook payload: %s", str(e))
        return False
    except Exception as e:
        logger.error("Error processing webhook: %s", str(e))
        return False


# Function removed - functionality now handled by verify_payment
