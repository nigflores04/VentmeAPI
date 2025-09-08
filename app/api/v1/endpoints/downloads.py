import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.db import client as db_client
from app.services.cloudfront_service import build_cloudfront_url

router = APIRouter(prefix="/downloads", tags=["downloads"])


@router.get("/generation/{job_id}")
async def download_generation(job_id: str):
    """Download a generated image by job ID."""
    # Find the generation job
    job = await db_client.prisma.generationjob.find_unique(where={"id": job_id})
    
    if not job or job.status != "done" or not job.output:
        raise HTTPException(status_code=404, detail="Generation not found or not ready")
    
    # Get CloudFront URL
    file_url = build_cloudfront_url(job.output)
    
    # Fetch file content and stream to frontend
    async with httpx.AsyncClient() as client:
        response = await client.get(file_url)
        response.raise_for_status()
        
        return StreamingResponse(
            iter([response.content]),
            media_type="image/png",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Content-Disposition": f"attachment; filename={job_id}.png"
            }
        )
