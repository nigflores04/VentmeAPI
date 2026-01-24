from typing import Optional, List

from pydantic import BaseModel, Field, field_validator, HttpUrl
from app.core.validators import (
    validate_image_dimensions,
    validate_room_type,
    validate_style_preset,
    validate_prompt_length
)


class ImageGenRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    width: int = Field(default=512, ge=256, le=2048)
    height: int = Field(default=512, ge=256, le=2048)
    seed: Optional[int] = Field(None, ge=0)
    
    @field_validator('width', 'height')
    @classmethod
    def validate_dimensions(cls, v: int, info) -> int:
        """Validate image dimensions."""
        # Get both width and height for validation
        if info.field_name == 'height':
            width = info.data.get('width', 512)
            validate_image_dimensions(width, v)
        return v


class ImageGenResponse(BaseModel):
    image_base64: str
    width: int
    height: int
    model: str


class GenerationRequest(BaseModel):
    prompt: Optional[str] = Field(None, max_length=500)
    room_type: Optional[str] = Field(
        default=None,
        description="Room type, e.g., 'Bedroom', 'Living room', 'Office', 'Studio', 'Kitchen', 'Bathroom'",
    )
    style_preset: Optional[str] = Field(
        default=None,
        description="Style preset, e.g., 'Minimalist', 'Cozy', 'Modern', 'Scandinavian', 'Industrial'",
    )
    width: int = Field(default=768, ge=256, le=2048)
    height: int = Field(default=512, ge=256, le=2048)
    
    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v: Optional[str]) -> Optional[str]:
        """Validate prompt length."""
        if v:
            validate_prompt_length(v)
        return v
    
    @field_validator('room_type')
    @classmethod
    def validate_room(cls, v: Optional[str]) -> Optional[str]:
        """Validate room type."""
        validate_room_type(v)
        return v
    
    @field_validator('style_preset')
    @classmethod
    def validate_style(cls, v: Optional[str]) -> Optional[str]:
        """Validate style preset."""
        validate_style_preset(v)
        return v


class GenerationResponse(BaseModel):
    image_base64: str
    width: int
    height: int
    model: str


class GenerationJobCreate(BaseModel):
    prompt: Optional[str] = Field(None, max_length=500)
    room_type: Optional[str] = None
    style_preset: Optional[str] = None
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)
    
    @field_validator('prompt')
    @classmethod
    def validate_prompt(cls, v: Optional[str]) -> Optional[str]:
        if v:
            validate_prompt_length(v)
        return v


class GenerationJobOut(BaseModel):
    id: str
    status: str
    reference: str
    output: Optional[str] = None
    prompt: Optional[str] = None
    room_type: Optional[str] = None
    style_preset: Optional[str] = None
    user: Optional[str] = None


class GenerationVariationsResponse(BaseModel):
    success: bool = True
    message: str = "Generation variations created successfully"
    prompt: Optional[str] = None
    room_type: Optional[str] = None
    style_preset: Optional[str] = None
    project_id: Optional[str] = None
    variations: List[GenerationJobOut] = []


class FileUploadResponse(BaseModel):
    success: bool = True
    message: str = "File uploaded successfully"
    url: str
    filename: str
    content_type: str
    size_bytes: int
