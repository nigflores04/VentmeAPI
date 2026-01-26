"""
Enhanced validation utilities for Ventics AI API.
"""

import re
from typing import Optional
from app.core.config import settings
from app.core.exceptions import ValidationError


def validate_password_strength(password: str) -> None:
    """
    Validate password meets security requirements.
    
    Raises:
        ValidationError: If password doesn't meet requirements
    """
    errors = []
    
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long")
    
    if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if settings.PASSWORD_REQUIRE_DIGIT and not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)")
    
    if errors:
        raise ValidationError(
            message="; ".join(errors),
            field="password",
            details={"requirements": errors}
        )


def validate_image_dimensions(width: int, height: int, min_size: int = 256, max_size: int = 2048) -> None:
    """
    Validate image dimensions are within acceptable range.
    
    Raises:
        ValidationError: If dimensions are invalid
    """
    if width < min_size or width > max_size:
        raise ValidationError(
            message=f"Width must be between {min_size} and {max_size} pixels",
            field="width",
            details={"min": min_size, "max": max_size, "provided": width}
        )
    
    if height < min_size or height > max_size:
        raise ValidationError(
            message=f"Height must be between {min_size} and {max_size} pixels",
            field="height",
            details={"min": min_size, "max": max_size, "provided": height}
        )


def validate_room_type(room_type: Optional[str]) -> None:
    """Validate room type is from allowed list."""
    if room_type is None:
        return
    
    allowed_types = {
        "bedroom", "living_room", "kitchen", "bathroom", "office",
        "dining_room", "studio", "hallway", "balcony", "outdoor"
    }
    
    if room_type.lower() not in allowed_types:
        raise ValidationError(
            message=f"Invalid room type. Allowed: {', '.join(sorted(allowed_types))}",
            field="room_type",
            details={"allowed": sorted(allowed_types), "provided": room_type}
        )


def validate_style_preset(style_preset: Optional[str]) -> None:
    """Validate style preset is from allowed list."""
    if style_preset is None:
        return
    
    allowed_styles = {
        "minimalist", "modern", "scandinavian", "industrial", "cozy",
        "bohemian", "traditional", "contemporary", "rustic", "luxury"
    }
    
    if style_preset.lower() not in allowed_styles:
        raise ValidationError(
            message=f"Invalid style preset. Allowed: {', '.join(sorted(allowed_styles))}",
            field="style_preset",
            details={"allowed": sorted(allowed_styles), "provided": style_preset}
        )


def validate_prompt_length(prompt: Optional[str], max_length: int = 500) -> None:
    """Validate prompt length."""
    if prompt and len(prompt) > max_length:
        raise ValidationError(
            message=f"Prompt must not exceed {max_length} characters",
            field="prompt",
            details={"max_length": max_length, "provided_length": len(prompt)}
        )
