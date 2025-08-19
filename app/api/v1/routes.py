from fastapi import APIRouter
from app.api.v1.endpoints import auth, remodels

api_router = APIRouter()

# Group v1 endpoints here
api_router.include_router(auth.router)
api_router.include_router(remodels.router)
