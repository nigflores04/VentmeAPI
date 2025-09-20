import uuid
import logging
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.models.schemas import FileUploadResponse
from app.services.storage_service import upload_bytes
from app.core.auth import get_current_user_optional, get_current_user_required

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/file", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(..., description="File to upload to S3"),
    key_prefix: Optional[str] = "uploads/",
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Upload a file to S3 storage.
    Returns the S3 URL and file metadata.
    """
    try:
        if not settings.S3_BUCKET:
            raise HTTPException(
                status_code=500,
                detail="S3 storage not configured"
            )

        # Validate file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {max_size // (1024*1024)}MB"
            )

        # Validate file type (images only for now)
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        content_type = file.content_type or "application/octet-stream"
        
        if content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed types: {', '.join(allowed_types)}"
            )

        # Generate unique filename
        file_extension = "png"  # Default to PNG
        if content_type == "image/jpeg" or content_type == "image/jpg":
            file_extension = "jpg"
        elif content_type == "image/webp":
            file_extension = "webp"
            
        unique_filename = f"{uuid.uuid4().hex[:16]}.{file_extension}"

        # Upload to S3 using the same logic as generation jobs
        file_url = upload_bytes(
            file_content,
            content_type=content_type,
            key_prefix=key_prefix,
            filename=unique_filename,
        )

        logger.info(f"File uploaded successfully: {unique_filename} ({len(file_content)} bytes)")

        return FileUploadResponse(
            url=file_url,
            filename=unique_filename,
            content_type=content_type,
            size_bytes=len(file_content)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=e.status_code,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.post("/reference", response_model=FileUploadResponse)
async def upload_reference_image(
    image: UploadFile = File(..., description="Image file to upload for generation input"),
    current_user: Optional[dict] = Depends(get_current_user_required),
):
    """
    Upload an image file specifically for use as generation input.
    Uses the same S3 path structure as generation jobs.
    """
    return await upload_file(
        file=image,
        key_prefix="generations/input/",
        current_user=current_user
    )
