from typing import Optional, List

from pydantic import BaseModel, Field


class ImageGenRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    width: int = 512
    height: int = 512
    seed: Optional[int] = None


class ImageGenResponse(BaseModel):
    image_base64: str
    width: int
    height: int
    model: str


class GenerationRequest(BaseModel):
    prompt: Optional[str] = None
    room_type: Optional[str] = Field(
        default=None,
        description="Room type, e.g., 'Bedroom', 'Living room', 'Office', 'Studio', 'Kitchen', 'Bathroom'",
    )
    style_preset: Optional[str] = Field(
        default=None,
        description="Style preset, e.g., 'Minimalist', 'Cozy', 'Modern', 'Scandinavian', 'Industrial'",
    )
    width: int = 768
    height: int = 512


class GenerationResponse(BaseModel):
    image_base64: str
    width: int
    height: int
    model: str


class GenerationJobCreate(BaseModel):
    prompt: Optional[str] = None
    room_type: Optional[str] = None
    style_preset: Optional[str] = None
    width: int = 1024
    height: int = 1024


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
    variations: List[GenerationJobOut] = []


class FileUploadResponse(BaseModel):
    success: bool = True
    message: str = "File uploaded successfully"
    url: str
    filename: str
    content_type: str
    size_bytes: int
