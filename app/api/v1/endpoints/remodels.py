from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, Response

from app.core.config import settings
from app.models.schemas import RemodelJobOut
from app.services.remodel_service import enqueue_remodel_job, process_job
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/remodel", tags=["remodel"])


@router.post("", response_model=RemodelJobOut, status_code=202)
async def create_remodel_job(
    response: Response,
    background: BackgroundTasks,
    image: UploadFile = File(..., description="Room photo to remodel"),
    prompt: Optional[str] = Form(None),
    style: Optional[str] = Form(None),
    items: Optional[str] = Form(None, description="Comma-separated list of items"),
    width: int = Form(1024),
    height: int = Form(1024),
    wait: bool = Form(True),
):
    try:
        if width > settings.MAX_IMAGE_SIZE or height > settings.MAX_IMAGE_SIZE:
            width = min(width, settings.MAX_IMAGE_SIZE)
            height = min(height, settings.MAX_IMAGE_SIZE)

        content_type = image.content_type or "image/png"
        data = await image.read()
        # Normalize items: split, trim, drop empties; if empty result, set to None
        logger.info("/v1/remodel POST received: content_type=%s, items_raw=%s", content_type, items)
        if items:
            tokens = [s.strip() for s in items.split(",") if s.strip()]
            items_list = tokens if tokens else None
        else:
            items_list = None
        logger.info("Parsed items_list=%s", items_list)

        job = await enqueue_remodel_job(
            image_bytes=data,
            content_type=content_type,
            prompt=prompt,
            style=style,
            items=items_list,
            width=width,
            height=height,
            user_id=None,  # TODO: wire JWT user
        )

        logger.info("Enqueued remodel job id=%s status=%s", job["id"], job["status"])  # type: ignore

        if wait:
            # Run processing inline and return the completed job (or failed) in this POST response
            logger.info("Starting inline processing for job id=%s", job["id"])  # type: ignore
            await process_job(job["id"])  # type: ignore
            from app.db import client as db_client
            if db_client.prisma is None:
                await db_client.connect()
            final = await db_client.prisma.remodeljob.find_unique(where={"id": job["id"]})  # type: ignore
            if not final:
                raise HTTPException(status_code=404, detail="Job not found after processing")
            items_val = final.items if isinstance(final.items, list) else None  # type: ignore[attr-defined]
            logger.info("Inline processing completed for job id=%s status=%s", final.id, final.status)
            # If failed, return a minimal error body via HTTP 500
            if str(final.status).lower() == "failed":
                raise HTTPException(
                    status_code=500,
                    detail={
                        "id": final.id,
                        "status": final.status,
                        "error": final.error,
                    },
                )
            # Success -> 200 with full payload
            response.status_code = 200
            return {
                "id": final.id,
                "status": final.status,
                "inputImageUrl": final.inputImageUrl,
                "outputImageUrl": final.outputImageUrl,
                "error": final.error,
                "prompt": final.prompt,
                "style": final.style,
                "items": items_val,
                "width": final.width,
                "height": final.height,
            }

        # Schedule background processing
        background.add_task(process_job, job["id"])  # type: ignore
        logger.info("Scheduled background processing for job id=%s", job["id"])  # type: ignore
        return {
            "id": job["id"],
            "status": job["status"],
            "inputImageUrl": job["inputImageUrl"],
            "outputImageUrl": job.get("outputImageUrl"),
            "error": job.get("error"),
            "prompt": job.get("prompt"),
            "style": job.get("style"),
            "items": job.get("items"),
            "width": job["width"],
            "height": job["height"],
        }
    except Exception as e:
        logger.exception("Error in create_remodel_job: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{job_id}", response_model=RemodelJobOut)
async def get_remodel_job(job_id: str):
    from app.db import client as db_client

    if db_client.prisma is None:
        await db_client.connect()
    job = await db_client.prisma.remodeljob.find_unique(where={"id": job_id})  # type: ignore
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Convert items JSON to list if needed
    items = job.items if isinstance(job.items, list) else None  # type: ignore[attr-defined]
    return {
        "id": job.id,
        "status": job.status,
        "inputImageUrl": job.inputImageUrl,
        "outputImageUrl": job.outputImageUrl,
        "error": job.error,
        "prompt": job.prompt,
        "style": job.style,
        "items": items,
        "width": job.width,
        "height": job.height,
    }
