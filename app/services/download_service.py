import asyncio
import base64
from io import BytesIO
import httpx
import replicate
from app.core.config import settings

replicate_client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)

async def replicate_upscale_image(image_url: str, scale: int = 2):
    output = replicate_client.run(
        "nightmareai/real-esrgan",
        input={
            "image":image_url,
            "scale": scale,
            "face_enhance": False
        }
    )


    if hasattr(output, "url"):
        output_url = output.url
    else:
        output_url = str(output)  

    # Download the upscaled image
    async with httpx.AsyncClient() as client:
        resp = await client.get(output_url)
        resp.raise_for_status()
        buffer = BytesIO(resp.content)
        buffer.seek(0)
        return buffer
    # return output.url()


