from __future__ import annotations

import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings


def generate_verification_code() -> str:
    """Generate a 4-digit verification code (0000-9999)"""
    return f"{secrets.randbelow(10000):04d}"


def get_code_expiration() -> datetime:
    """Get expiration time for verification code (10 minutes from now)"""
    return datetime.now(timezone.utc) + timedelta(minutes=10)


async def send_verification_email(email: str, code: str, name: Optional[str] = None) -> bool:
    """Send verification code email via SMTP"""
    if not all([settings.SMTP_HOST, settings.SMTP_USERNAME, settings.SMTP_PASSWORD, settings.SMTP_FROM_EMAIL]):
        print(f"Email service not configured - would send code {code} to {email}")
        return True  # Return success for development
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM_EMAIL
        msg['To'] = email
        msg['Subject'] = "Verify your Ventics AI account"
        
        # Email body
        greeting = f"Hi {name}," if name else "Hi,"
        body = f"""
{greeting}

Your verification code is: {code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
Ventics AI Team
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"Verification email sent to {email}")
        return True
        
    except Exception as e:
        print(f"Failed to send email to {email}: {e}")
        return False


def is_code_expired(expires_at: Optional[datetime]) -> bool:
    """Check if verification code has expired"""
    if not expires_at:
        return True
    return datetime.now(timezone.utc) > expires_at


def can_attempt_verification(attempts: int) -> bool:
    """Check if user can still attempt verification (max 3 attempts)"""
    return attempts < 3
