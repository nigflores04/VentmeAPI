from typing import Dict
from app.models.payment_schemas import SubscriptionPlan

# Credit plan pricing configuration
SUBSCRIPTION_PLANS: Dict[SubscriptionPlan, Dict] = {
    SubscriptionPlan.FREE: {
        "credits": 5,
        "price": 0,  # ₦6,500.00 (equivalent to ~$4)
        "description": "Perfect for trying out our AI remodeling service",
        "popular": False
    },
    SubscriptionPlan.STARTER: {
        "credits": 40,
        "price": 650000,  # ₦6,500.00 (equivalent to ~$4)
        "description": "Perfect for trying out our AI remodeling service",
        "popular": False
    },
    SubscriptionPlan.BASIC: {
        "credits": 80,
        "price": 1250000,  # ₦12,500.00 (equivalent to ~$8)
        "description": "Great for small projects and regular use",
        "popular": True
    },
    SubscriptionPlan.PREMIUM: {
        "credits": 160,
        "price": 2400000,  # ₦24,000.00 (equivalent to ~$15)
        "description": "Best value for frequent users and professionals",
        "popular": False
    },
    # SubscriptionPlan.PROFESSIONAL: {
    #     "credits": 300,
    #     "price": 4000000,  # ₦40,000.00 (equivalent to ~$25)
    #     "description": "For heavy users and design professionals",
    #     "popular": False
    # }
}



def get_plan_details(plan: SubscriptionPlan) -> Dict:
    """Get the complete configuration for a subscription plan"""
    return SUBSCRIPTION_PLANS.get(plan, {})