from typing import Optional
from datetime import datetime

<<<<<<< HEAD
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.core.validators import validate_password_strength
=======
from pydantic import BaseModel, EmailStr, Field
>>>>>>> origin/master


class RegisterRequest(BaseModel):
    email: EmailStr
<<<<<<< HEAD
    password: str = Field(..., min_length=8, max_length=128)
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        validate_password_strength(v)
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate name doesn't contain invalid characters."""
        if v and any(char in v for char in ['<', '>', '{', '}', '\\']):
            raise ValueError("Name contains invalid characters")
        return v
=======
    password: str = Field(..., min_length=8)
    name: Optional[str] = None
>>>>>>> origin/master


class LoginRequest(BaseModel):
    email: EmailStr
<<<<<<< HEAD
    password: str = Field(..., min_length=1, max_length=128)
=======
    password: str
>>>>>>> origin/master


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., description="Google ID token from client")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: Optional[datetime] = None


class UserPublic(BaseModel):
    id: str
    email: EmailStr
<<<<<<< HEAD
    name: Optional[str] = Field(None, max_length=100)
    emailVerified: bool = False
    credits: int = Field(default=1, ge=0)  # Credits cannot be negative
=======
    name: Optional[str] = None
    emailVerified: bool = False
    credits: int = 1
>>>>>>> origin/master


class VerifyEmailRequest(BaseModel):
    email: EmailStr
<<<<<<< HEAD
    code: str = Field(..., min_length=4, max_length=6, pattern=r'^\d{4,6}$')
    
    @field_validator('code')
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        """Ensure code is numeric."""
        if not v.isdigit():
            raise ValueError("Verification code must contain only digits")
        return v
=======
    code: str = Field(..., min_length=4, max_length=4)
>>>>>>> origin/master


class ResendCodeRequest(BaseModel):
    email: EmailStr


class AuthResponse(BaseModel):
    email: EmailStr
    token: TokenResponse
    message: Optional[str] = None
