from typing import Dict
from app.models.payment_schemas import SubscriptionPlan

# Credit plan pricing configuration
# Prices are in kobo (Nigerian currency): 1 Naira = 100 kobo
# Example: ₦7,500 = 750000 kobo

SUBSCRIPTION_PLANS: Dict[SubscriptionPlan, Dict] = {
    SubscriptionPlan.FREE: {
        "credits": 9,  # 3 requests (9 credits) per week
        "price": 0,  # Free plan
        "description": "Watermarked renders · 3 requests (9 credits) per week · New credits restore in 7 days when existing credit is exhausted",
        "popular": False,
        "features": [
            {"name": "Dashboard Access", "included": True},
            {"name": "Customer Support", "included": True},
            {"name": "3 requests per week", "included": True},
            {"name": "High Resolution Downloads", "included": False},
            {"name": "Projects Management Tool", "included": False},
            {"name": "3D Visualization", "included": False},
            {"name": "Product Discovery", "included": False},
            {"name": "Shareable Link", "included": False},
            {"name": "Priority Support", "included": False}
        ]
    },
    SubscriptionPlan.STARTER: {
        "credits": 120,  # 40 requests (120 credits)
        "price": 750000,  # ₦7,500.00
        "description": "40 requests (120 credits) · High resolution download · Projects management dashboard/tool",
        "popular": False,
        "features": [
            {"name": "Dashboard Access", "included": True},
            {"name": "Customer Support", "included": True},
            {"name": "40 requests", "included": True},
            {"name": "High Resolution Downloads", "included": True},
            {"name": "Projects Management Tool", "included": True},
            {"name": "3D Visualization", "included": False},
            {"name": "Product Discovery", "included": False},
            {"name": "Shareable Link", "included": False},
            {"name": "Priority Support", "included": False}
        ]
    },
    SubscriptionPlan.BASIC: {
        "credits": 240,  # 80 requests (240 credits)
        "price": 1200000,  # ₦12,000.00
        "description": "80 requests (240 credits) · High resolution download · Projects management · 3D visualization",
        "popular": True,
        "features": [
            {"name": "Dashboard Access", "included": True},
            {"name": "Customer Support", "included": True},
            {"name": "80 requests", "included": True},
            {"name": "High Resolution Downloads", "included": True},
            {"name": "Projects Management Tool", "included": True},
            {"name": "3D Visualization", "included": True},
            {"name": "Product Discovery", "included": False},
            {"name": "Shareable Link", "included": False},
            {"name": "Priority Support", "included": False}
        ]
    },
    SubscriptionPlan.STUDIO: {
        "credits": 450,  # 150 requests (450 credits)
        "price": 2500000,  # ₦25,000.00
        "description": "Unlimited · All features · Priority Support",
        "popular": False,
        "features": [
            {"name": "Dashboard Access", "included": True},
            {"name": "Customer Support", "included": True},
            {"name": "Unlimited requests", "included": True},
            {"name": "High Resolution Downloads", "included": True},
            {"name": "Projects Management Tool", "included": True},
            {"name": "3D Visualization", "included": True},
            {"name": "Product Discovery", "included": True},
            {"name": "Shareable Link", "included": True},
            {"name": "Priority Support", "included": True}
        ]
    }
}

# Individual plan configuration - flexible credit purchase
# ₦100 per credit (10000 kobo per credit)
INDIVIDUAL_PLAN = {
    "name": "Individual",
    "price_per_credit": 10000,  # ₦100 per credit in kobo
    "minimum_credits": 1,
    "minimum_amount": 10000,  # ₦100 minimum purchase in kobo
    "description": "Purchase a flexible amount of credits for your needs",
    "features": [
        {"name": "₦100 per credit", "included": True},
        {"name": "No subscription required", "included": True},
        {"name": "Credits never expire", "included": True},
        {"name": "Buy exactly what you need", "included": True}
    ]
}



def get_plan_details(plan: SubscriptionPlan) -> Dict:
    """Get the complete configuration for a subscription plan"""
    return SUBSCRIPTION_PLANS.get(plan, {})


def get_individual_credit_price() -> int:
    """Get the price per credit for individual purchases (in kobo)"""
    return 10000  # ₦100 per credit