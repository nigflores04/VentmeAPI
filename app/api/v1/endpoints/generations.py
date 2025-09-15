from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, Response

from app.core.config import settings
from app.core.auth import get_current_user_optional
from app.models.schemas import GenerationJobOut, GenerationVariationsResponse
from app.services.generations_service import enqueue_generation_job, process_generation_job
import logging
import time
from app.db import client as db_client
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generations", tags=["generations"])


@router.post("", response_model=GenerationJobOut, status_code=202)
async def create_generation_job(
    response: Response,
    # image: UploadFile = File(..., description="Room photo to transform"),
    image: str = Form(..., description="S3 URL of the room photo to transform"),
    prompt: Optional[str] = Form(None, description="Text description for the generation"),
    room_type: Optional[str] = Form(None, description="Room type: Bedroom, Living room, Office, Studio, Kitchen, Bathroom"),
    style_preset: Optional[str] = Form(None, description="Style preset: Minimalist, Cozy, Modern, Scandinavian, Industrial"),
    width: int = Form(1024),
    height: int = Form(1024),
    wait: bool = Form(True),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    try:
        if width > settings.MAX_IMAGE_SIZE or height > settings.MAX_IMAGE_SIZE:
            width = min(width, settings.MAX_IMAGE_SIZE)
            height = min(height, settings.MAX_IMAGE_SIZE)

        # content_type = image.content_type or "image/png"
        # data = await image.read()
        # logger.info("/v1/generations POST received: content_type=%s, room_type=%s, style_preset=%s", content_type, room_type, style_preset)

        # Check user credits and apply restrictions for anonymous users
        user_id = None
        if current_user:
            user_id = current_user["id"]
            if current_user["credits"] < 1:
                raise HTTPException(
                    status_code=402,  # Payment Required
                    detail="Insufficient credits. You need at least 1 credit to create a generation job."
                )
        else:
            # Anonymous user restrictions
            if style_preset is not None:
                raise HTTPException(
                    status_code=401,
                    detail="Style preset customization requires authentication. Please sign up or log in."
                )
            if room_type is not None:
                raise HTTPException(
                    status_code=401,
                    detail="Room type specification requires authentication. Please sign up or log in."
                )
            if width != 1024 or height != 1024:
                raise HTTPException(
                    status_code=401,
                    detail="Custom dimensions require authentication. Please sign up or log in."
                )
            if prompt and len(prompt) > 100:
                raise HTTPException(
                    status_code=401,
                    detail="Long prompts require authentication. Please keep prompts under 100 characters or sign up."
                )
            # Force basic settings for anonymous users
            width = 1024
            height = 1024

        job = await enqueue_generation_job(
            # image_bytes=data,
            # content_type=content_type,
            image_url=image,
            prompt=prompt,
            room_type=room_type,
            style_preset=style_preset,
            width=width,
            height=height,
            user_id=user_id,
        )

        logger.info("Enqueued generation job id=%s status=%s", job["id"], job["status"]) 

        if wait:
            # Run processing inline and return the completed job (or failed) in this POST response
            logger.info("Starting inline processing for job id=%s", job["id"]) 
            await process_generation_job(job["id"]) 

            final = await db_client.prisma.generationjob.find_unique(where={"id": job["id"]}) 
            if not final:
                raise HTTPException(status_code=404, detail="Job not found after processing")
            
            logger.info("Inline processing completed for job id=%s status=%s", final.id, final.status)
            # If failed, return a minimal error body via HTTP 500 (truncate long errors)
            if str(final.status).lower() == "failed":
                err = (final.error or "").strip()
                if len(err) > 300:
                    err = err[:300] + "... [truncated]"
                raise HTTPException(
                    status_code=500,
                    detail={
                        "id": final.id,
                        "status": final.status,
                        "error": err,
                    },
                )
            # Success -> 200 with full payload
            response.status_code = 200
            return {
                "id": final.id,
                "status": final.status,
                "reference": final.reference,
                "output": final.output,
                "prompt": final.prompt,
                "room_type": final.room_type,
                "style_preset": final.style_preset,
                "user": final.userId,
            }

        # Schedule background processing
        # background.add_task(process_generation_job, job["id"]) 
        # logger.info("Scheduled background processing for job id=%s", job["id"]) 
        # return {
        #     "id": job["id"],
        #     "status": job["status"],
        #     "reference": job["reference"],
        #     "output": job.get("output"),
        #     "prompt": job.get("prompt"),
        #     "style": job.get("style"),
        #     "items": job.get("items"),
        #     "width": job["width"],
        #     "height": job["height"],
        # }
    except Exception as e:
        logger.exception("Error in create_generation_job: %s", e)
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.post("/variations", response_model=GenerationVariationsResponse)
async def create_generation_variations(
    response: Response,
    # image: UploadFile = File(..., description="Room photo to transform"),
    image: str = Form(..., description="S3 URL of the room photo to transform"),
    prompt: Optional[str] = Form(None, description="Text description for the generation"),
    room_type: Optional[str] = Form(None, description="Room type: Bedroom, Living room, Office, Studio, Kitchen, Bathroom"),
    style_preset: Optional[str] = Form(None, description="Style preset: Minimalist, Cozy, Modern, Scandinavian, Industrial"),
    width: int = Form(1024),
    height: int = Form(1024),
    num_variations: int = Form(3, description="Number of design variations to generate (1-5)"),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Generate multiple design variations for a single input image.
    Returns a combined response with details of all variations.
    """
    try:

        if num_variations < 1 or num_variations > 5:
            raise HTTPException(
                status_code=400,
                detail="Number of variations must be between 1 and 5"
            )
            
        if width > settings.MAX_IMAGE_SIZE or height > settings.MAX_IMAGE_SIZE:
            width = min(width, settings.MAX_IMAGE_SIZE)
            height = min(height, settings.MAX_IMAGE_SIZE)

        # content_type = image.content_type or "image/png"
        # data = await image.read()
        logger.info("/v1/generations/variations POST received: content_type=%s, variations=%d", 
                   # content_type, 
                   num_variations)

        # Check user credits and apply restrictions for anonymous users
        user_id = None
        if current_user:
            user_id = current_user["id"]
            if current_user["credits"] < num_variations:
                raise HTTPException(
                    status_code=402,  # Payment Required
                    detail=f"Insufficient credits. You need at least {num_variations} credits to create {num_variations} variations."
                )
        else:
            # Anonymous users can only generate 1 variation
            if num_variations > 1:
                raise HTTPException(
                    status_code=401,
                    detail="Multiple variations require authentication. Please sign up or log in."
                )
                
            # Apply other anonymous user restrictions
            if style_preset is not None:
                raise HTTPException(
                    status_code=401,
                    detail="Style preset customization requires authentication. Please sign up or log in."
                )
            if room_type is not None:
                raise HTTPException(
                    status_code=401,
                    detail="Room type specification requires authentication. Please sign up or log in."
                )
            if width != 1024 or height != 1024:
                raise HTTPException(
                    status_code=401,
                    detail="Custom dimensions require authentication. Please sign up or log in."
                )
            if prompt and len(prompt) > 100:
                raise HTTPException(
                    status_code=401,
                    detail="Long prompts require authentication. Please keep prompts under 100 characters or sign up."
                )
            # Force basic settings for anonymous users
            width = 1024
            height = 1024

        # Create jobs for all variations first
        job_ids = []
        for i in range(num_variations):
            # Create a job for each variation
            job = await enqueue_generation_job(
                # image_bytes=data,
                # content_type=content_type,
                image_url=image,
                prompt=prompt,
                room_type=room_type,
                style_preset=style_preset,
                width=width,
                height=height,
                user_id=user_id,
            )
            job_ids.append(job["id"])
            logger.info(f"Created variation job")
        
        # Process jobs with staggered start times to reduce API pressure
        start_time = time.time()
        logger.info(f"Starting processing of {len(job_ids)} variation jobs")
        
        async def process_and_get_job(job_id):
            try:
                await process_generation_job(job_id)
                final = await db_client.prisma.generationjob.find_unique(where={"id": job_id})
                if not final:
                    logger.error(f"Job not found after processing")
                    return None
                
                # Only return jobs that have successfully completed with an output URL
                if final.status != "done" or not final.output:
                    logger.warning(f"Job completed with status {final.status} but no output URL")
                    return None
                
                return {
                    "id": final.id,
                    "status": final.status,
                    "reference": final.reference,
                    "output": final.output,
                    "prompt": final.prompt,
                    "room_type": final.room_type,
                    "style_preset": final.style_preset,
                    "user": final.userId,
                }
            except Exception as e:
                logger.error(f"Error processing job {job_id}: {str(e)}")
                return None

        tasks = []
        for i, job_id in enumerate(job_ids):
            # Add a small delay between starting each job to prevent simultaneous API calls
            async def delayed_process(job_id, delay):
                if delay > 0:
                    await asyncio.sleep(delay)
                return await process_and_get_job(job_id)
            
            tasks.append(delayed_process(job_id, i * 0.5))  # 500ms delay between starts

        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        logger.info(f"Completed processing {len(job_ids)} variation jobs in {total_time:.2f} seconds")
        
        # Filter out any None results (failed jobs)
        variation_jobs = [job for job in results if job is not None]
        successful_jobs = len(variation_jobs)
        failed_jobs = len(job_ids) - successful_jobs
        
        logger.info(f"Variations summary: {successful_jobs} successful, {failed_jobs} failed, total time: {total_time:.2f}s")
            
        # Return combined response with all variations
        return {
            "success": True,
            "message": f"Generated {len(variation_jobs)} design variations",
            "prompt": prompt,
            "room_type": room_type,
            "style_preset": style_preset,
            "variations": variation_jobs
        }
            
    except Exception as e:
        logger.exception("Error in create_generation_variations: %s", e)
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get("/{job_id}", response_model=GenerationJobOut)
async def get_generation_job(job_id: str):
    from app.db import client as db_client

    if db_client.prisma is None:
        await db_client.connect()
    job = await db_client.prisma.generationjob.find_unique(where={"id": job_id})  # type: ignore
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "status": job.status,
        "reference": job.reference,
        "output": job.output,
        "prompt": job.prompt,
        "room_type": job.room_type,
        "style_preset": job.style_preset,
        "user": job.userId,
    }
