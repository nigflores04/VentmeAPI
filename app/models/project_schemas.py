from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.schemas import GenerationJobOut


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    description: Optional[str] = Field(None, max_length=500, description="Project description")
    referenceImage: Optional[str] = Field(None, description="Initial reference image URL")
    prompt: Optional[str] = Field(None, description="Initial prompt")
    room_type: Optional[str] = Field(None, description="Initial room type")
    style_preset: Optional[str] = Field(None, description="Initial style preset")


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Project name")
    description: Optional[str] = Field(None, max_length=500, description="Project description")
    isActive: Optional[bool] = Field(None, description="Whether the project is active")
    referenceImage: Optional[str] = Field(None, description="Reference image URL")
    prompt: Optional[str] = Field(None, description="Prompt")
    room_type: Optional[str] = Field(None, description="Room type")
    style_preset: Optional[str] = Field(None, description="Style preset")


class GenerationGroup(BaseModel):
    """Group of generation variations with the same parameters"""
    reference: str
    prompt: Optional[str] = None
    room_type: Optional[str] = None
    style_preset: Optional[str] = None
    created_at: datetime
    variations: List[GenerationJobOut] = []


class ProjectOut(BaseModel):
    id: str
    userId: str
    name: str
    description: Optional[str] = None
    isActive: bool
    referenceImage: Optional[str] = None
    prompt: Optional[str] = None
    room_type: Optional[str] = None
    style_preset: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    generationCount: int = 0  # Total number of generations in this project
    generations: List[GenerationJobOut] = []


class ProjectWithGenerations(ProjectOut):
    generations: List[GenerationJobOut] = []  # Simple flat list of generation jobs


class ProjectListResponse(BaseModel):
    success: bool = True
    message: str = "Projects retrieved successfully"
    projects: List[ProjectOut] = []
    total: int = 0


class ProjectResponse(BaseModel):
    success: bool = True
    message: str = "Project retrieved successfully"
    project: ProjectOut


class ProjectCreateResponse(BaseModel):
    success: bool = True
    message: str = "Project created successfully"
    project: ProjectOut


class ProjectUpdateResponse(BaseModel):
    success: bool = True
    message: str = "Project updated successfully"
    project: ProjectOut


class ProjectDeleteResponse(BaseModel):
    success: bool = True
    message: str = "Project deleted successfully"


# Moodboard Schemas
class MoodboardCreate(BaseModel):
    projectId: str = Field(..., description="Project ID to associate the moodboard with")
    referenceImage: str = Field(..., description="Reference image URL for moodboard generation")
    prompt: Optional[str] = Field(None, max_length=1000, description="Additional prompt for moodboard style")
    style: Optional[str] = Field(None, description="Style preference for the moodboard")
    colorPalette: Optional[str] = Field(None, description="Color palette preference")


class MoodboardItem(BaseModel):
    """Individual item in a moodboard"""
    title: str
    description: str
    category: str  # e.g., "color", "texture", "furniture", "lighting", "decor"
    imageUrl: Optional[str] = None
    hexColor: Optional[str] = None  # For color items
    

class MoodboardOut(BaseModel):
    id: str
    projectId: str
    userId: str
    referenceImage: str
    prompt: Optional[str] = None
    style: Optional[str] = None
    colorPalette: Optional[str] = None
    status: str  # "generating", "completed", "failed"
    items: List[MoodboardItem] = []
    output: Optional[str] = None  # S3 URL of the generated moodboard image
    createdAt: datetime
    updatedAt: datetime


class MoodboardResponse(BaseModel):
    success: bool = True
    message: str = "Moodboard generated successfully"
    moodboard: MoodboardOut


class MoodboardListResponse(BaseModel):
    success: bool = True
    message: str = "Moodboards retrieved successfully"
    moodboards: List[MoodboardOut] = []
    total: int = 0
