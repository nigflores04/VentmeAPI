from typing import Dict, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.models.payment_schemas import SubscriptionPlan
from app.core.payment_config import SUBSCRIPTION_PLANS, INDIVIDUAL_PLAN
from app.core.auth import get_current_user_required

router = APIRouter(prefix="/plans", tags=["plans"])


class PlanFeature(BaseModel):
    name: str
    included: bool


class PlanResponse(BaseModel):
    plan: SubscriptionPlan
    credits: int
    price: int
    description: str
    popular: bool
    features: List[PlanFeature]


class PlanCreate(BaseModel):
    credits: int
    price: int
    description: str
    popular: bool = False


class PlanUpdate(BaseModel):
    credits: int = None
    price: int = None
    description: str = None
    popular: bool = None


@router.get("", response_model=List[PlanResponse])
async def get_all_plans():
    """Get all subscription plans."""
    plans = []
    for plan, config in SUBSCRIPTION_PLANS.items():
        plans.append(PlanResponse(
            plan=plan,
            credits=config["credits"],
            price=config["price"],
            description=config["description"],
            popular=config["popular"],
            features=[PlanFeature(**feature) for feature in config["features"]]
        ))
    return plans


class IndividualPlanResponse(BaseModel):
    name: str
    price_per_credit: int
    minimum_credits: int
    minimum_amount: int
    description: str
    features: List[PlanFeature]


@router.get("/individual", response_model=IndividualPlanResponse)
async def get_individual_plan():
    """Get Individual plan configuration for flexible credit purchases."""
    return IndividualPlanResponse(
        name=INDIVIDUAL_PLAN["name"],
        price_per_credit=INDIVIDUAL_PLAN["price_per_credit"],
        minimum_credits=INDIVIDUAL_PLAN["minimum_credits"],
        minimum_amount=INDIVIDUAL_PLAN["minimum_amount"],
        description=INDIVIDUAL_PLAN["description"],
        features=[PlanFeature(**feature) for feature in INDIVIDUAL_PLAN["features"]]
    )


@router.get("/{plan}", response_model=PlanResponse)
async def get_plan(plan: SubscriptionPlan):
    """Get a specific subscription plan."""
    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    config = SUBSCRIPTION_PLANS[plan]
    return PlanResponse(
        plan=plan,
        credits=config["credits"],
        price=config["price"],
        description=config["description"],
        popular=config["popular"],
        features=[PlanFeature(**feature) for feature in config["features"]]
    )


@router.post("/{plan}", response_model=PlanResponse)
async def create_plan(
    plan: SubscriptionPlan,
    plan_data: PlanCreate,
    current_user: dict = Depends(get_current_user_required)
):
    """Create a new subscription plan (admin only)."""
    if plan in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Plan already exists")
    
    SUBSCRIPTION_PLANS[plan] = {
        "credits": plan_data.credits,
        "price": plan_data.price,
        "description": plan_data.description,
        "popular": plan_data.popular
    }
    
    return PlanResponse(
        plan=plan,
        credits=plan_data.credits,
        price=plan_data.price,
        description=plan_data.description,
        popular=plan_data.popular
    )


@router.put("/{plan}", response_model=PlanResponse)
async def update_plan(
    plan: SubscriptionPlan,
    plan_data: PlanUpdate,
    current_user: dict = Depends(get_current_user_required)
):
    """Update an existing subscription plan (admin only)."""
    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    config = SUBSCRIPTION_PLANS[plan]
    
    if plan_data.credits is not None:
        config["credits"] = plan_data.credits
    if plan_data.price is not None:
        config["price"] = plan_data.price
    if plan_data.description is not None:
        config["description"] = plan_data.description
    if plan_data.popular is not None:
        config["popular"] = plan_data.popular
    
    return PlanResponse(
        plan=plan,
        credits=config["credits"],
        price=config["price"],
        description=config["description"],
        popular=config["popular"]
    )


@router.delete("/{plan}")
async def delete_plan(
    plan: SubscriptionPlan,
    current_user: dict = Depends(get_current_user_required)
):
    """Delete a subscription plan (admin only)."""
    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    del SUBSCRIPTION_PLANS[plan]
    return {"message": f"Plan {plan.value} deleted successfully"}
