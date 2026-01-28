from __future__ import annotations

import os
import secrets
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings


def generate_verification_code() -> str:
    """Generate a 4-digit verification code (0000-9999)"""
    return f"{secrets.randbelow(10000):04d}"


def get_code_expiration() -> datetime:
    """Get expiration time for verification code (10 minutes from now)"""
    return datetime.now(timezone.utc) + timedelta(minutes=10)


async def send_verification_email(email: str, code: str, name: Optional[str] = None) -> bool:
    """Send verification code email via Mailgun REST API"""
    mailgun_api_key = settings.MAILGUN_API_KEY
    mailgun_domain = settings.MAILGUN_DOMAIN
    from_email = settings.SMTP_FROM_EMAIL
    
    if not mailgun_api_key or not mailgun_domain or not from_email:
        print(f"Mailgun not configured - would send code {code} to {email}")
        return True  # Return success for development
    
    try:
        # Email body
        greeting = f"Hi {name}," if name else "Hi,"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Verify your Ventics AI account</h2>
            <p>{greeting}</p>
            <p>Your verification code is: <strong style="font-size: 18px; color: #007bff;">{code}</strong></p>
            <p>This code will expire in 10 minutes.</p>
            <p>If you didn't request this code, please ignore this email.</p>
            <p>Best regards,<br>The Ventics AI Team</p>
        </div>
        """
        
        text_content = f"""
{greeting}

Your verification code is: {code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
The Ventics AI Team
        """
        
        # Send email via Mailgun API
        mailgun_url = f"https://api.mailgun.net/v3/{mailgun_domain}/messages"
        response = requests.post(
            mailgun_url,
            auth=("api", mailgun_api_key),
            data={
                "from": from_email,
                "to": email,
                "subject": "Verify your Ventics AI account",
                "text": text_content,
                "html": html_content
            }
        )
        
        if response.status_code == 200:
            print(f"Verification email sent to {email}")
            return True
        else:
            print(f"Mailgun API error: {response.status_code} - {response.text}")
            return False
        
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
