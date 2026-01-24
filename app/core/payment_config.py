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
            "Watermarked renders",
            "3 requests (9 credits) per week",
            "Credits restore in 7 days"
        ]
    },
    SubscriptionPlan.STARTER: {
        "credits": 120,  # 40 requests (120 credits)
        "price": 750000,  # ₦7,500.00
        "description": "40 requests (120 credits) · High resolution download · Projects management dashboard/tool",
        "popular": False,
        "features": [
            "40 requests (120 credits)",
            "High resolution download",
            "Projects management dashboard/tool"
        ]
    },
    SubscriptionPlan.BASIC: {
        "credits": 240,  # 80 requests (240 credits)
        "price": 1200000,  # ₦12,000.00
        "description": "80 requests (240 credits) · High resolution download · Projects management · 3D visualization",
        "popular": True,
        "features": [
            "80 requests (240 credits)",
            "High resolution download",
            "Projects management dashboard/tool",
            "3D visualization"
        ]
    },
    SubscriptionPlan.STUDIO: {
        "credits": 450,  # 150 requests (450 credits)
        "price": 2500000,  # ₦25,000.00
        "description": "Unlimited (150 requests/450 credits) · All features · Priority Support",
        "popular": False,
        "features": [
            "150 requests (450 credits)",
            "High resolution download",
            "Product discovery",
            "3D visualization",
            "Projects management dashboard/tool",
            "Shareable link",
            "Priority Support"
        ]
    },
    # Individual plan - flexible credit purchase
    # ₦100 per credit (10000 kobo per credit)
}



def get_plan_details(plan: SubscriptionPlan) -> Dict:
    """Get the complete configuration for a subscription plan"""
    return SUBSCRIPTION_PLANS.get(plan, {})


def get_individual_credit_price() -> int:
    """Get the price per credit for individual purchases (in kobo)"""
    return 10000  # ₦100 per credit