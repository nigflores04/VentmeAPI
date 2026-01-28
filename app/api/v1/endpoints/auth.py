from fastapi import APIRouter, HTTPException, status

from app.models.auth_schemas import AuthResponse, GoogleLoginRequest, LoginRequest, RegisterRequest, VerifyEmailRequest, ResendCodeRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    try:
        return await auth_service.register(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    try:
        return await auth_service.login(req)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/google", response_model=AuthResponse)
async def login_google(req: GoogleLoginRequest):
    try:
        return await auth_service.login_with_google(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-email")
async def verify_email(req: VerifyEmailRequest):
    try:
        return await auth_service.verify_email(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resend-code")
async def resend_code(req: ResendCodeRequest):
    try:
        return await auth_service.resend_verification_code(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
