from typing import Optional
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., description="Google ID token from client")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: Optional[datetime] = None


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    emailVerified: bool = False
    credits: int = 1


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=4, max_length=4)


class ResendCodeRequest(BaseModel):
    email: EmailStr


class AuthResponse(BaseModel):
    email: EmailStr
    token: TokenResponse
    message: Optional[str] = None
