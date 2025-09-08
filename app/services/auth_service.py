from __future__ import annotations

import uuid
import logging
from datetime import timedelta
from typing import Optional

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.auth_schemas import (
    AuthResponse,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
    VerifyEmailRequest,
    ResendCodeRequest,
)
from app.db import client as db_client
from os import getenv
from app.services.verification_service import send_verification_code, verify_email_code

logger = logging.getLogger(__name__)



async def register(req: RegisterRequest) -> AuthResponse:
    DATABASE_URL = getenv("DATABASE_URL")

    # Ensure Prisma is connected
    if not DATABASE_URL:
        raise ValueError("Database not configured")
    
    if db_client.prisma is None:
        try:
            await db_client.connect()
            print("register: connected to database")
        except Exception as e:
            raise ValueError(f"Database connection failed: {e}")
    
    if not db_client.prisma.is_connected():  # type: ignore[attr-defined]
        raise ValueError("Database not connected")

    existing = await db_client.prisma.user.find_unique(where={"email": req.email})
    if existing:
        raise ValueError("Email already registered")
    
    user_id = str(uuid.uuid4())
    created = await db_client.prisma.user.create(
        data={
            "id": user_id,
            "email": req.email,
            "name": req.name,
            "passwordHash": hash_password(req.password),
            "provider": "password",
        }
    )
    logger.info("register: created user id=%s email=%s (DB)", created.id, created.email)
    
    if created.provider == "password":
        try:
            await send_verification_code(created.email, created.name)
            logger.info("Verification code sent to %s", created.email)
        except Exception as e:
            logger.error("Failed to send verification code to %s: %s", created.email, e)
    
    token_data = create_access_token(subject=created.id, email=created.email, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    return AuthResponse(
        email=created.email,
        token=TokenResponse(access_token=token_data["token"], expires_at=token_data["expires_at"]),
        message="Account created successfully. A verification code has been sent to your email.",
    )


async def login(req: LoginRequest) -> AuthResponse:
    if not settings.DATABASE_URL:
        raise ValueError("Database not configured")
    
    if db_client.prisma is None:
        try:
            await db_client.connect()
        except Exception as e:
            raise ValueError(f"Database connection failed: {e}")
    
    if not db_client.prisma.is_connected():  # type: ignore[attr-defined]
        raise ValueError("Database not connected")

    logger.info("login: using DB lookup for email=%s", req.email)
    db_user = await db_client.prisma.user.find_unique(where={"email": req.email})
    
    # Check if user exists
    if not db_user:
        raise ValueError("User with email not found")
    
    # Check if user has a password (not a Google user trying to login with password)
    if not db_user.passwordHash:
        raise ValueError("This account uses Google login. Please sign in with Google.")
    
    # Check password
    if not verify_password(req.password, db_user.passwordHash):
        raise ValueError("Password incorrect")
    
    # Use getattr with default False for backward compatibility
    email_verified = getattr(db_user, 'emailVerified', False)
    # DISABLED: Email verification temporarily disabled for development
    # if not email_verified and db_user.provider == "password":
    #     try:
    #         await send_verification_code(db_user.email, db_user.name)
    #         logger.info("Verification reminder sent to %s", db_user.email)
    #     except Exception as e:
    #         logger.error("Failed to send verification reminder to %s: %s", db_user.email, e)
    
    token_data = create_access_token(subject=db_user.id, email=db_user.email, expires_delta=timedelta(days=1))
    return AuthResponse(
        email=db_user.email,
        token=TokenResponse(access_token=token_data["token"], expires_at=token_data.get("expires_at")),
    )


async def login_with_google(req: GoogleLoginRequest) -> AuthResponse:
    if not settings.GOOGLE_CLIENT_ID:
        raise ValueError("Google login not configured")
    # Verify Google ID token
    idinfo = google_id_token.verify_oauth2_token(req.id_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
    if idinfo.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise ValueError("Invalid Google token issuer")

    email = idinfo.get("email")
    name = idinfo.get("name") or idinfo.get("given_name")
    if not email:
        raise ValueError("Google token missing email")

    if not settings.DATABASE_URL:
        raise ValueError("Database not configured")
    
    if db_client.prisma is None:
        try:
            await db_client.connect()
        except Exception as e:
            raise ValueError(f"Database connection failed: {e}")
    
    if not db_client.prisma.is_connected():  # type: ignore[attr-defined]
        raise ValueError("Database not connected")

    logger.info("google login: using DB for email=%s", email)
    db_user = await db_client.prisma.user.find_unique(where={"email": email})
    if not db_user:
        db_user = await db_client.prisma.user.create(
            data={
                "id": str(uuid.uuid4()),
                "email": email,
                "name": name,
                "passwordHash": None,
                "provider": "google",
            }
        )
    # Auto-verify Google users
    email_verified_google = getattr(db_user, 'emailVerified', False)
    if not email_verified_google:
        await db_client.prisma.user.update(
            where={"email": email},
            data={"emailVerified": True}
        )
        email_verified_google = True
    
    logger.info("google login: user id=%s email=%s (DB)", db_user.id, db_user.email)
    token_data = create_access_token(subject=db_user.id, email=db_user.email, expires_delta=timedelta(days=1))
    return AuthResponse(
        email=db_user.email,
        token=TokenResponse(access_token=token_data["token"], expires_at=token_data.get("expires_at")),
    )


async def verify_email(req: VerifyEmailRequest) -> dict:
    """Verify email with 4-digit code"""
    if not settings.DATABASE_URL:
        raise ValueError("Database not configured")
    
    if db_client.prisma is None:
        try:
            await db_client.connect()
        except Exception as e:
            raise ValueError(f"Database connection failed: {e}")
    
    try:
        success = await verify_email_code(req.email, req.code)
        if success:
            return {"message": "Email verified successfully"}
        else:
            raise ValueError("Verification failed")
    except Exception as e:
        raise ValueError(str(e))


async def resend_verification_code(req: ResendCodeRequest) -> dict:
    """Resend verification code to user's email"""
    if not settings.DATABASE_URL:
        raise ValueError("Database not configured")
    
    if db_client.prisma is None:
        try:
            await db_client.connect()
        except Exception as e:
            raise ValueError(f"Database connection failed: {e}")
    
    # Find user
    user = await db_client.prisma.user.find_unique(where={"email": req.email})
    if not user:
        raise ValueError("User not found")
    
    user_email_verified = getattr(user, 'emailVerified', False)
    if user_email_verified:
        return {"message": "Email already verified"}
    
    if user.provider == "google":
        # Auto-verify Google users
        await db_client.prisma.user.update(
            where={"email": req.email},
            data={"emailVerified": True}
        )
        return {"message": "Email verified (Google user)"}
    
    try:
        success = await send_verification_code(req.email, user.name)
        if success:
            return {"message": "Verification code sent"}
        else:
            raise ValueError("Failed to send verification code")
    except Exception as e:
        raise ValueError(str(e))
