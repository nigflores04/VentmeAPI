from fastapi import APIRouter
from app.api.v1.endpoints import auth, generations, users, payments, subscriptions, uploads, downloads, plans, emails, projects, products

api_router = APIRouter()

# Group v1 endpoints here
api_router.include_router(auth.router)
api_router.include_router(generations.router)
api_router.include_router(users.router)
api_router.include_router(payments.router)
api_router.include_router(subscriptions.router)
api_router.include_router(uploads.router)
api_router.include_router(downloads.router)
api_router.include_router(plans.router)
api_router.include_router(emails.router)
api_router.include_router(projects.router)
api_router.include_router(products.router)
