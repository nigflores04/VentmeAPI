from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import app.db.client as db_client
from app.core.config import settings
from app.services.email_service import (
    generate_verification_code,
    get_code_expiration,
    send_verification_email,
    is_code_expired,
    can_attempt_verification,
)

logger = logging.getLogger(__name__)


async def send_verification_code(email: str, name: Optional[str] = None) -> bool:
    """Generate and send verification code to user"""
    if not settings.DATABASE_URL or not db_client.prisma:
        raise ValueError("Database not configured")
    
    # Find user
    user = await db_client.prisma.user.find_unique(where={"email": email})
    if not user:
        raise ValueError("User not found")
    
    # Skip verification for Google users
    if user.provider == "google":
        await db_client.prisma.user.update(
            where={"email": email},
            data={"emailVerified": True}
        )
        return True
    
    # Generate new code
    code = generate_verification_code()
    expires_at = get_code_expiration()
    
    # Update user with new code
    await db_client.prisma.user.update(
        where={"email": email},
        data={
            "verificationCode": code,
            "codeExpiresAt": expires_at,
            "codeAttempts": 0,  # Reset attempts
        }
    )
    
    # Send email
    success = await send_verification_email(email, code, name or user.name)
    if success:
        logger.info("Verification code sent to %s", email)
    else:
        logger.error("Failed to send verification code to %s", email)
    
    return success


async def verify_email_code(email: str, code: str) -> bool:
    """Verify the email verification code"""
    if not settings.DATABASE_URL or not db_client.prisma:
        raise ValueError("Database not configured")
    
    # Find user
    user = await db_client.prisma.user.find_unique(where={"email": email})
    if not user:
        raise ValueError("User not found")
    
    # Check if already verified
    user_email_verified = getattr(user, 'emailVerified', False)
    if user_email_verified:
        return True
    
    # Check if code exists and not expired
    if not user.verificationCode or is_code_expired(user.codeExpiresAt):
        raise ValueError("Verification code expired or not found")
    
    # Check attempts
    if not can_attempt_verification(user.codeAttempts):
        raise ValueError("Too many verification attempts")
    
    # Verify code
    if user.verificationCode != code:
        # Increment attempts
        await db_client.prisma.user.update(
            where={"email": email},
            data={"codeAttempts": user.codeAttempts + 1}
        )
        raise ValueError("Invalid verification code")
    
    # Success - mark as verified and clear code
    await db_client.prisma.user.update(
        where={"email": email},
        data={
            "emailVerified": True,
            "verificationCode": None,
            "codeExpiresAt": None,
            "codeAttempts": 0,
        }
    )
    
    logger.info("Email verified for %s", email)
    return True


async def is_user_verified(email: str) -> bool:
    """Check if user's email is verified"""
    if not settings.DATABASE_URL or not db_client.prisma:
        return False
    
    user = await db_client.prisma.user.find_unique(where={"email": email})
    return getattr(user, 'emailVerified', False) if user else False
