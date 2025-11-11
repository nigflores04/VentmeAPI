import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.db import client as db_client
from app.services.cloudfront_service import build_cloudfront_url
from PIL import Image
from io import BytesIO
from app.services.download_service import replicate_upscale_image
from app.services.subscription_service import get_active_subscription
from app.models.payment_schemas import SubscriptionPlan

router = APIRouter(prefix="/downloads", tags=["downloads"])


@router.get("/generation/{job_id}")
async def download_generation(job_id: str, scale: int = None):
    """Download a generated image by job ID."""
    if db_client.prisma is None:
        await db_client.connect()

    # Find the generation job
    job = await db_client.prisma.generationjob.find_unique(where={"id": job_id})
    
    if not job or job.status != "done" or not job.output:
        raise HTTPException(status_code=404, detail="Generation not found or not ready")
    
    # Get CloudFront URL
    file_url = build_cloudfront_url(job.output)

    # Fetch file content and stream to frontend
    try:
        if scale:
            if not job.userId:
                raise HTTPException(status_code=401, detail="Authentication required to download high-resolution images")

            subscription = await get_active_subscription(job.userId)
            if not subscription or subscription.plan not in {SubscriptionPlan.BASIC, SubscriptionPlan.PREMIUM}:
                raise HTTPException(
                    status_code=402,
                    detail="A Basic or Premium subscription is required to download high-resolution images",
                )

            buffer = await replicate_upscale_image(file_url, scale)

            return StreamingResponse(
                buffer,
                media_type="image/png",
                headers={"Content-Disposition": "attachment; filename={job_id}_{scale}.png"},
            )

        else:
            print(f"Downloading original image")
            async with httpx.AsyncClient() as client:
                response = await client.get(file_url)
                response.raise_for_status()
                
                return StreamingResponse(
                    iter([response.content]),
                    media_type="image/png",
                    headers={"Content-Disposition": "attachment; filename={job_id}_original.png"},
                )

    except Exception as e:
        return {"error": str(e)}