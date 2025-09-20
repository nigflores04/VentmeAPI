from typing import List, Optional
import logging
import paystack
from datetime import datetime, timedelta
import uuid

from app.core.config import settings
from app.db import client as db_client
from app.models.payment_schemas import (
    SubscriptionDetails, 
    SubscriptionStatus,
    SubscriptionPlan,
    PaymentStatus
)
from app.core.payment_config import get_plan_details

logger = logging.getLogger(__name__)


async def get_user_subscriptions(user_id: str) -> List[SubscriptionDetails]:
    """Get all subscriptions for a user"""
    if db_client.prisma is None:
        await db_client.connect()
    
    # Find all subscription payments for this user
    subscription_payments = await db_client.prisma.payment.find_many(
        where={
            "userId": user_id,
            "isSubscription": True,
        }
    )
    
    # Group by plan to get unique subscriptions
    subscriptions_map = {}
    for payment in subscription_payments:
        try:
            # Get plan from payment
            plan = SubscriptionPlan(payment.plan)
            
            if plan.value not in subscriptions_map:
                # Determine subscription status based on payment status
                status = SubscriptionStatus.ACTIVE
                if payment.status == PaymentStatus.CANCELLED.value:
                    status = SubscriptionStatus.CANCELLED
                elif payment.status == PaymentStatus.FAILED.value:
                    status = SubscriptionStatus.EXPIRED
                
                # Get the Paystack plan code from transaction metadata
                # First, try to get it from Paystack transaction
                plan_code = None
                try:
                    # Verify the payment to get metadata
                    transaction_data = paystack.Transaction.verify(reference=payment.payment_reference)
                    if transaction_data and hasattr(transaction_data, 'data') and 'metadata' in transaction_data.data:
                        metadata = transaction_data.data['metadata']
                        if isinstance(metadata, dict) and 'plan_code' in metadata:
                            plan_code = metadata['plan_code']
                except Exception as e:
                    logger.warning(f"Could not retrieve plan code from Paystack: {str(e)}")
                
                # Fallback to generated code if not found
                if not plan_code:
                    plan_code = f"{plan.value}_monthly"
                    logger.warning(f"Using fallback plan code: {plan_code}")
                
                subscriptions_map[plan.value] = SubscriptionDetails(
                    id=payment.id,
                    plan=plan,
                    plan_code=plan_code,
                    status=status,
                    next_payment_date=None,  # We don't have this field yet
                    created_at=payment.createdAt,
                    last_payment_date=payment.completedAt
                )
        except (ValueError, AttributeError) as e:
            logger.error(f"Error processing payment {payment.id}: {str(e)}")
            continue
    
    return list(subscriptions_map.values())


async def get_subscription_details(subscription_id: str) -> Optional[SubscriptionDetails]:
    """Get details for a specific subscription"""
    if db_client.prisma is None:
        await db_client.connect()
    
    # Find the subscription payment
    payment = await db_client.prisma.payment.find_unique(
        where={"id": subscription_id}
    )
    
    if not payment or not payment.isSubscription:
        return None
    
    try:
        # Determine subscription status based on payment status
        status = SubscriptionStatus.ACTIVE
        if payment.status == PaymentStatus.CANCELLED.value:
            status = SubscriptionStatus.CANCELLED
        elif payment.status == PaymentStatus.FAILED.value:
            status = SubscriptionStatus.EXPIRED
        
        # Get the Paystack plan code from transaction metadata
        plan_code = None
        try:
            # Verify the payment to get metadata
            transaction_data = paystack.Transaction.verify(reference=payment.payment_reference)
            if transaction_data and hasattr(transaction_data, 'data') and 'metadata' in transaction_data.data:
                metadata = transaction_data.data['metadata']
                if isinstance(metadata, dict) and 'plan_code' in metadata:
                    plan_code = metadata['plan_code']
        except Exception as e:
            logger.warning(f"Could not retrieve plan code from Paystack: {str(e)}")
        
        # Fallback to generated code if not found
        if not plan_code:
            plan = SubscriptionPlan(payment.plan)
            plan_code = f"{plan.value}_monthly"
            logger.warning(f"Using fallback plan code: {plan_code}")
        
        return SubscriptionDetails(
            id=payment.id,
            plan=SubscriptionPlan(payment.plan),
            plan_code=plan_code,
            status=status,
            next_payment_date=None,  # We don't have this field yet
            created_at=payment.createdAt,
            last_payment_date=payment.completedAt
        )
    except (ValueError, AttributeError) as e:
        logger.error(f"Error processing subscription {subscription_id}: {str(e)}")
        return None


async def has_active_subscription(user_id: str) -> bool:
    """Check if a user has an active subscription"""
    if db_client.prisma is None:
        await db_client.connect()
    
    # Find active subscription payments for this user
    active_payments = await db_client.prisma.payment.find_many(
        where={
            "userId": user_id,
            "isSubscription": True,
            "status": PaymentStatus.SUCCESSFUL.value,
            "completedAt": {
                "gte": datetime.now().replace(day=1) # Current month
            }
        }
    )
    
    return len(active_payments) > 0


async def get_active_subscription(user_id: str) -> Optional[SubscriptionDetails]:
    """Get the active subscription for a user if one exists"""
    if db_client.prisma is None:
        await db_client.connect()
    
    # Find active subscription payments for this user
    active_payments = await db_client.prisma.payment.find_many(
        where={
            "userId": user_id,
            "isSubscription": True,
            "status": PaymentStatus.SUCCESSFUL.value,
            "completedAt": {
                "gte": datetime.now().replace(day=1) # Current month
            }
        },
        take=1
    )
    
    if not active_payments:
        return None
    
    payment = active_payments[0]
    
    #  plan code from plan name
    plan = SubscriptionPlan(payment.plan)
    plan_code = f"{plan.value}_monthly"
    
    # Get credits for the plan
    plan_details = get_plan_details(plan)
    credits = plan_details.get("credits", 0)
    next_payment_date = payment.completedAt + timedelta(days=30) if payment.completedAt else None
    
    return SubscriptionDetails(
        id=payment.id,
        plan=SubscriptionPlan(payment.plan),
        plan_code=plan_code,
        credits=credits, 
        status=SubscriptionStatus.ACTIVE,
        next_payment_date=next_payment_date,
        created_at=payment.createdAt,
        last_payment_date=payment.completedAt
    )

async def cancel_subscription(subscription_id: str) -> bool:
    """Cancel a subscription"""
    if not settings.PAYSTACK_SECRET_KEY:
        raise ValueError("Paystack not configured")
    
    if db_client.prisma is None:
        await db_client.connect()
    
    # Find the subscription payment
    payment = await db_client.prisma.payment.find_unique(
        where={"id": subscription_id}
    )
    
    if not payment or not payment.isSubscription:
        return False
    
    try:
        # Get user email
        user = await db_client.prisma.user.find_unique(
            where={"id": payment.userId}
        )
        
        if not user:
            logger.error(f"User not found for subscription {subscription_id}")
            return False
        
        # Generate plan code from plan name
        plan = SubscriptionPlan(payment.plan)
        plan_code = f"{plan.value}_monthly"
        
        # Find the subscription in Paystack
        subscriptions = paystack.Subscription.list(
            customer=user.email,
            plan=plan_code
        )
        
        # Check if the response has data attribute and contains subscriptions
        if not subscriptions or not hasattr(subscriptions, 'data') or not subscriptions.data or len(subscriptions.data) == 0:
            logger.warning(f"No Paystack subscription found for {subscription_id}, marking as cancelled anyway")
            # Update the subscription in our database even if not found in Paystack
            await db_client.prisma.payment.update(
                where={"id": subscription_id},
                data={"status": PaymentStatus.CANCELLED.value}
            )
            return True
        
        # Cancel the subscription in Paystack
        subscription_code = subscriptions.data[0].subscription_code
        result = paystack.Subscription.disable(
            code=subscription_code,
            token=subscriptions.data[0].email_token
        )
        
        # Update the subscription in our database regardless of Paystack result
        await db_client.prisma.payment.update(
            where={"id": subscription_id},
            data={"status": PaymentStatus.CANCELLED.value}
        )
        
        logger.info(f"Cancelled subscription {subscription_id}")
        return True
            
    except Exception as e:
        logger.error(f"Error cancelling subscription {subscription_id}: {str(e)}")
        return False
