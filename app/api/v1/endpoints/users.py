from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user_required
from app.models.schemas import GenerationJobOut
from app.models.auth_schemas import UserPublic
from app.db import client as db_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])



@router.get("/", response_model=List[UserPublic])
async def get_all_users(
    current_user: dict = Depends(get_current_user_required),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
):
    """
    Get all users. Requires authentication.
    Supports pagination with skip and limit parameters.
    """
    try:
        users = await db_client.prisma.user.find_many(
            skip=skip,
            take=limit,
            order={"createdAt": "desc"}
        )
        
        return [
            UserPublic(
                id=user.id,
                email=user.email,
                name=user.name,
                emailVerified=user.emailVerified,
                credits=user.credits,
            )
            for user in users
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )
        
@router.get("/me", response_model=UserPublic)
async def get_current_user_details(
    current_user: dict = Depends(get_current_user_required),
):
    """
    Get current authenticated user's details including credits.
    """
    return UserPublic(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user.get("name"),
        emailVerified=current_user.get("emailVerified", False),
        credits=current_user.get("credits", 1),
    )


@router.get("/me/generations", response_model=List[GenerationJobOut])
async def get_user_generations(
    current_user: dict = Depends(get_current_user_required),
    status: Optional[str] = Query(None, description="Filter by status: queued, running, done, failed"),
    limit: int = Query(20, ge=1, le=100, description="Number of jobs to return (1-100)"),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
):
    """
    Get all remodel jobs/projects for the authenticated user.
    Supports filtering by status and pagination.
    """

    where_clause = {"userId": current_user["id"]}
    if status:
        if status not in ["queued", "running", "done", "failed"]:
            raise HTTPException(status_code=400, detail="Invalid status. Must be one of: queued, running, done, failed")
        where_clause["status"] = status
    
    # Fetch user's generation jobs with pagination
    jobs = await db_client.prisma.generationjob.find_many(
        where=where_clause,
        take=limit,
        skip=offset,
        order={"createdAt": "desc"},
    )
    
    # Convert to response format
    result = []
    for job in jobs:
        result.append({
            "id": job.id,
            "status": job.status,
            "reference": job.reference,
            "output": job.output,
            "prompt": job.prompt,
            "room_type": job.room_type,
            "style_preset": job.style_preset,
            "user": job.userId,
        })
    
    logger.info("Retrieved %d remodel jobs for user %s", len(result), current_user["id"])
    return result


@router.get("/me/generations/count")
async def get_user_generations_jobs_count(
    current_user: dict = Depends(get_current_user_required),
    status: Optional[str] = Query(None, description="Filter by status: queued, running, done, failed"),
):
    """
    Get count of remodel jobs for the authenticated user.
    Supports filtering by status.
    """
    if db_client.prisma is None:
        await db_client.connect()
    
    # Build where clause
    where_clause = {"userId": current_user["id"]}
    if status:
        if status not in ["queued", "running", "done", "failed"]:
            raise HTTPException(status_code=400, detail="Invalid status. Must be one of: queued, running, done, failed")
        where_clause["status"] = status
    
    # Get count
    count = await db_client.prisma.generationjob.count(where=where_clause)  # type: ignore
    
    return {"count": count, "status": status or "all"}
