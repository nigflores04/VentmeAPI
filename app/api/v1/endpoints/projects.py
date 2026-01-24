from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from app.core.auth import get_current_user_required
from app.models.project_schemas import (
    ProjectCreate, 
    ProjectUpdate, 
    ProjectOut, 
    ProjectWithGenerations,
    ProjectListResponse,
    ProjectResponse,
    ProjectCreateResponse,
    ProjectUpdateResponse,
    ProjectDeleteResponse
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectCreateResponse)
async def create_project(
    data: ProjectCreate,
    current_user: dict = Depends(get_current_user_required)
):
    """Create a new project for the authenticated user."""
    try:
        project = await ProjectService.create_project(current_user["id"], data)
        return ProjectCreateResponse(project=project)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/", response_model=ProjectListResponse)
async def get_user_projects(
    skip: int = Query(0, ge=0, description="Number of projects to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of projects to return"),
    include_inactive: bool = Query(False, description="Include inactive projects"),
    current_user: dict = Depends(get_current_user_required)
):
    """Get all projects for the authenticated user."""
    try:
        projects = await ProjectService.get_user_projects(
            current_user["id"], 
            skip=skip, 
            limit=limit, 
            include_inactive=include_inactive
        )
        return ProjectListResponse(
            projects=projects,
            total=len(projects)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve projects: {str(e)}")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user_required)
):
    """Get a specific project with all its generations."""
    try:
        project = await ProjectService.get_project_by_id(project_id, current_user["id"])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectResponse(project=project)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve project: {str(e)}")


@router.put("/{project_id}", response_model=ProjectUpdateResponse)
async def update_project(
    project_id: str,
    update_data: ProjectUpdate,
    current_user: dict = Depends(get_current_user_required)
):
    """Update a project's details."""
    try:
        project = await ProjectService.update_project(project_id, current_user["id"], update_data)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectUpdateResponse(project=project)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")


@router.delete("/{project_id}", response_model=ProjectDeleteResponse)
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user_required)
):
    """Delete a project. Associated generations will have their project association removed."""
    try:
        success = await ProjectService.delete_project(project_id, current_user["id"])
        if not success:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return ProjectDeleteResponse()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")


@router.post("/{project_id}/generations/{generation_id}")
async def add_generation_to_project(
    project_id: str,
    generation_id: str,
    current_user: dict = Depends(get_current_user_required)
):
    """Associate an existing generation with a project."""
    try:
        success = await ProjectService.add_generation_to_project(
            project_id, generation_id, current_user["id"]
        )
        if not success:
            raise HTTPException(
                status_code=404, 
                detail="Project or generation not found, or generation doesn't belong to user"
            )
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Generation added to project successfully"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add generation to project: {str(e)}")


@router.delete("/generations/{generation_id}")
async def remove_generation_from_project(
    generation_id: str,
    current_user: dict = Depends(get_current_user_required)
):
    """Remove a generation from its project."""
    try:
        success = await ProjectService.remove_generation_from_project(
            generation_id, current_user["id"]
        )
        if not success:
            raise HTTPException(
                status_code=404, 
                detail="Generation not found or doesn't belong to user"
            )
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Generation removed from project successfully"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove generation from project: {str(e)}")
