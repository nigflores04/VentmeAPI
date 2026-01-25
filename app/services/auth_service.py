from __future__ import annotations

import uuid
import logging
from datetime import timedelta
from typing import Optional

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.core.exceptions import (
    AuthenticationError,
    ValidationError,
    DatabaseError,
    ExternalServiceError
)
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
    """
    Register a new user with email and password.
    
    Flow:
    1. Validate database connection
    2. Check if email already exists
    3. Create new user with hashed password
    4. Allocate 9 FREE CREDITS (3 generations × 3 credits each)
    5. Send verification email
    6. Return authentication token
    
    Args:
        req: RegisterRequest containing email, name, and password
        
    Returns:
        AuthResponse with access token and user email
        
    Raises:
        DatabaseError: If database is not configured or connection fails
        ValidationError: If email is already registered
    """
    DATABASE_URL = getenv("DATABASE_URL")
    logger.info(f"[REGISTER] Starting registration for email: {req.email}")

    # Ensure Prisma is connected
    if not DATABASE_URL:
        logger.error("[REGISTER] Database URL not configured")
        raise DatabaseError("Database not configured")
    
    if db_client.prisma is None:
        try:
            await db_client.connect()
            logger.info("[REGISTER] Connected to database")
        except Exception as e:
            logger.error(f"[REGISTER] Database connection failed: {e}")
            raise DatabaseError(f"Database connection failed: {e}")
    
    if not db_client.prisma.is_connected():  # type: ignore[attr-defined]
        logger.error("[REGISTER] Database not connected")
        raise DatabaseError("Database not connected")

    # Check if email already exists
    existing = await db_client.prisma.user.find_unique(where={"email": req.email})
    if existing:
        logger.warning(f"[REGISTER] Email already registered: {req.email}")
        raise ValidationError("Email already registered", field="email")
    
    # Create new user with FREE CREDITS
    user_id = str(uuid.uuid4())
    logger.info(f"[REGISTER] Creating user with ID: {user_id}")
    created = await db_client.prisma.user.create(
        data={
            "id": user_id,
            "email": req.email,
            "name": req.name,
            "passwordHash": hash_password(req.password),
            "provider": "password",
            "credits": 9  # FREE PLAN: 9 credits = 3 generations (3 credits per generation)
        }
    )
    logger.info(f"[REGISTER] ✅ User created successfully - ID: {created.id}, Email: {created.email}, Credits: 9")
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
    """
    Authenticate user with email and password.
    
    Flow:
    1. Validate database connection
    2. Find user by email
    3. Verify user exists and has password (not Google OAuth user)
    4. Verify password matches
    5. Return authentication token (valid for 1 week)
    
    Args:
        req: LoginRequest containing email and password
        
    Returns:
        AuthResponse with access token and user email
        
    Raises:
        DatabaseError: If database is not configured or connection fails
        AuthenticationError: If credentials are invalid or user uses Google login
    """
    logger.info(f"[LOGIN] Login attempt for email: {req.email}")
    
    if not settings.DATABASE_URL:
        logger.error("[LOGIN] Database not configured")
        raise DatabaseError("Database not configured")
    
    if db_client.prisma is None:
        try:
            await db_client.connect()
            logger.info("[LOGIN] Connected to database")
        except Exception as e:
            logger.error(f"[LOGIN] Database connection failed: {e}")
            raise DatabaseError(f"Database connection failed: {e}")
    
    if not db_client.prisma.is_connected():  # type: ignore[attr-defined]
        logger.error("[LOGIN] Database not connected")
        raise DatabaseError("Database not connected")

    # Find user by email
    logger.info(f"[LOGIN] Looking up user: {req.email}")
    db_user = await db_client.prisma.user.find_unique(where={"email": req.email})
    
    # Check if user exists
    if not db_user:
        logger.warning(f"[LOGIN] ❌ User not found: {req.email}")
        raise AuthenticationError("Invalid email or password")  # Don't reveal which field is wrong
    
    # Check if user has a password (not a Google user trying to login with password)
    if not db_user.passwordHash:
        logger.warning(f"[LOGIN] ❌ Google user attempting password login: {req.email}")
        raise AuthenticationError("This account uses Google login. Please sign in with Google.")
    
    # Verify password
    if not verify_password(req.password, db_user.passwordHash):
        logger.warning(f"[LOGIN] ❌ Invalid password for user: {req.email}")
        raise AuthenticationError("Invalid email or password")  # Don't reveal which field is wrong
    
    logger.info(f"[LOGIN] ✅ Login successful - User: {db_user.email}, Credits: {db_user.credits}")
    
    # Use getattr with default False for backward compatibility
    email_verified = getattr(db_user, 'emailVerified', False)
    # DISABLED: Email verification temporarily disabled for development
    # if not email_verified and db_user.provider == "password":
    #     try:
    #         await send_verification_code(db_user.email, db_user.name)
    #         logger.info("Verification reminder sent to %s", db_user.email)
    #     except Exception as e:
    #         logger.error("Failed to send verification reminder to %s: %s", db_user.email, e)
    
    token_data = create_access_token(subject=db_user.id, email=db_user.email, expires_delta=timedelta(weeks=1))
    return AuthResponse(
        email=db_user.email,
        token=TokenResponse(access_token=token_data["token"], expires_at=token_data.get("expires_at")),
    )


async def login_with_google(req: GoogleLoginRequest) -> AuthResponse:
    """
    Authenticate user with Google OAuth.
    
    Flow:
    1. Verify Google ID token
    2. Extract email and name from token
    3. Find or create user in database
    4. Auto-verify email and allocate 9 FREE CREDITS for new users
    5. Return authentication token (valid for 1 week)
    
    Args:
        req: GoogleLoginRequest containing Google ID token
        
    Returns:
        AuthResponse with access token and user email
        
    Raises:
        ExternalServiceError: If Google OAuth is not configured
        AuthenticationError: If Google token is invalid
        DatabaseError: If database connection fails
    """
    logger.info(f"[GOOGLE LOGIN] Starting Google OAuth login")
    
    if not settings.GOOGLE_CLIENT_ID:
        logger.error("[GOOGLE LOGIN] Google OAuth not configured")
        raise ExternalServiceError("Google", "Google login not configured")
    
    # Verify Google ID token
    try:
        logger.info("[GOOGLE LOGIN] Verifying Google ID token")
        idinfo = google_id_token.verify_oauth2_token(req.id_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
    except Exception as e:
        logger.error(f"[GOOGLE LOGIN] ❌ Invalid Google token: {e}")
        raise AuthenticationError(f"Invalid Google token: {str(e)}")
    
    # Validate token issuer
    if idinfo.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        logger.error(f"[GOOGLE LOGIN] ❌ Invalid token issuer: {idinfo.get('iss')}")
        raise AuthenticationError("Invalid Google token issuer")

    # Extract user info from token
    email = idinfo.get("email")
    name = idinfo.get("name") or idinfo.get("given_name")
    if not email:
        logger.error("[GOOGLE LOGIN] ❌ Google token missing email")
        raise AuthenticationError("Google token missing email")
    
    logger.info(f"[GOOGLE LOGIN] Token verified for email: {email}")

    if not settings.DATABASE_URL:
        logger.error("[GOOGLE LOGIN] Database not configured")
        raise DatabaseError("Database not configured")
    
    if db_client.prisma is None:
        try:
            await db_client.connect()
            logger.info("[GOOGLE LOGIN] Connected to database")
        except Exception as e:
            logger.error(f"[GOOGLE LOGIN] Database connection failed: {e}")
            raise ValueError(f"Database connection failed: {e}")
    
    if not db_client.prisma.is_connected():  # type: ignore[attr-defined]
        logger.error("[GOOGLE LOGIN] Database not connected")
        raise ValueError("Database not connected")

    # Find or create user
    logger.info(f"[GOOGLE LOGIN] Looking up user: {email}")
    db_user = await db_client.prisma.user.find_unique(where={"email": email})
    if not db_user:
        # Create new Google user
        user_id = str(uuid.uuid4())
        logger.info(f"[GOOGLE LOGIN] Creating new Google user - ID: {user_id}, Email: {email}")
        db_user = await db_client.prisma.user.create(
            data={
                "id": user_id,
                "email": email,
                "name": name,
        logger.info(f"[GOOGLE LOGIN] ✅ New user created: {email}")
    # Auto-verify Google users and allocate FREE CREDITS
    email_verified_google = getattr(db_user, 'emailVerified', False)
    if not email_verified_google:
        logger.info(f"[GOOGLE LOGIN] Auto-verifying email and allocating 9 FREE CREDITS for: {email}")
        await db_client.prisma.user.update(
            where={"email": email},
            data={"emailVerified": True, "credits": 9}  # FREE PLAN: 9 credits for new Google users
        )
        email_verified_google = True
        logger.info(f"[GOOGLE LOGIN] ✅ Email verified and credits allocated: {email}")
    
    logger.info(f"[GOOGLE LOGIN] ✅ Google login successful - User: {db_user.email}, Credits: {db_user.credits}")
    
    logger.info("google login: user id=%s email=%s (DB)", db_user.id, db_user.email)
    token_data = create_access_token(subject=db_user.id, email=db_user.email, expires_delta=timedelta(weeks=1))
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
