from typing import Optional

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


class RemodelRequest(BaseModel):
    prompt: Optional[str] = None
    style: Optional[str] = Field(
        default=None,
        description="Desired interior style, e.g., 'modern', 'minimalist', 'scandinavian'",
    )
    items: Optional[list[str]] = Field(
        default=None,
        description="Optional list of furniture/interior items to include",
    )
    width: int = 768
    height: int = 512


class RemodelResponse(BaseModel):
    image_base64: str
    width: int
    height: int
    model: str


class RemodelJobCreate(BaseModel):
    prompt: Optional[str] = None
    style: Optional[str] = None
    items: Optional[list[str]] = None
    width: int = 1024
    height: int = 1024


class RemodelJobOut(BaseModel):
    id: str
    status: str
    inputImageUrl: str
    outputImageUrl: Optional[str] = None
    error: Optional[str] = None
    prompt: Optional[str] = None
    style: Optional[str] = None
    items: Optional[list[str]] = None
    width: int
    height: int
