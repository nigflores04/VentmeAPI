from __future__ import annotations

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import decode_token
from app.db import client as db_client

security = HTTPBearer(auto_error=False)


async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    """
    Optional authentication dependency that returns user info if valid token is provided,
    or None if no token or invalid token.
    """
    if not credentials:
        return None
    
    token_data = decode_token(credentials.credentials)
    if not token_data:
        return None
    
    user_id = token_data.get("sub")
    if not user_id:
        return None
    
    # Ensure DB connection
    if db_client.prisma is None:
        await db_client.connect()
    
    user = await db_client.prisma.user.find_unique(where={"id": user_id})  # type: ignore
    if not user:
        return None
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "credits": getattr(user, 'credits', 1),
        "emailVerified": getattr(user, 'emailVerified', False),
    }


async def get_current_user_required(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Required authentication dependency that raises HTTPException if no valid token is provided.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Ensure DB connection
    if db_client.prisma is None:
        await db_client.connect()
    
    user = await db_client.prisma.user.find_unique(where={"id": user_id})  # type: ignore
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "credits": getattr(user, 'credits', 1),
        "emailVerified": getattr(user, 'emailVerified', False),
    }
