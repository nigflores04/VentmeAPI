from __future__ import annotations

import uuid
from typing import List, Optional
import os
import base64
import aiohttp
import tempfile
import logging
import time
from datetime import datetime
from google import genai
from PIL import Image

import httpx
import json
import io

from app.core.config import settings
from app.db import client as db_client
from app.models.schemas import GenerationJobOut
from app.services.storage_service import upload_bytes
from app.models.project_schemas import MoodboardOut, MoodboardItem

# Download the image from URL first
import aiohttp
import tempfile
import os
from dotenv import load_dotenv
import asyncio
from app.services.project_service import ProjectService

load_dotenv(override=True)


logger = logging.getLogger(__name__)

# Global semaphore to limit concurrent Gemini API requests
_gemini_semaphore = asyncio.Semaphore(2)  # Allow max 2 concurrent requests

async def enqueue_generation_job(
    *,
    # image_bytes: bytes,
    image_url: str,
    # content_type: str,
    prompt: Optional[str],
    room_type: Optional[str],
    style_preset: Optional[str],
    width: int,
    height: int,
    user_id: Optional[str],
    project_id: Optional[str],
) -> dict:
    if not settings.S3_BUCKET:
        raise RuntimeError("S3 not configured")
    # Ensure DB connection (avoid stale imported reference)
    if db_client.prisma is None:
        await db_client.connect()


    # Cap size to MAX_IMAGE_SIZE
    width = min(width, settings.MAX_IMAGE_SIZE)
    height = min(height, settings.MAX_IMAGE_SIZE)


    # Create job in DB (use relation connect for user)
    data: dict = {
        "id": str(uuid.uuid4()),
        "status": "queued",
        "reference": image_url,
        "prompt": prompt,
        "room_type": room_type,
        "style_preset": style_preset,
        "width": width,
        "height": height,
        # "userId": user_id,
        # "projectId": project_id,
    }

    print("User ID being passed: %s", user_id)
    print("Project ID being passed: %s", project_id)
    if user_id:
        data["user"] = {"connect": {"id": user_id}}
        # data["userId"] = {"connect": {"id": user_id}}
    if project_id:
        data["project"] = {"connect": {"id": project_id}}
        # data["projectId"] = {"connect": {"id": project_id}}

    logger.info("Creating GenerationJob with data keys=%s", list(data.keys()))
    logger.info("Project ID being passed: %s", project_id)
    
    try:
        job = await db_client.prisma.generationjob.create(  # type: ignore
            data=data
        )
        logger.info("GenerationJob created successfully with ID: %s", job.id)
        
        # If this generation is associated with a project, update the project's parameters
        if project_id:

            data["projectId"] = project_id
            logger.info("Updating project %s with generation parameters", project_id)
            
            success = await ProjectService.update_project_from_generation(
                project_id,
                image_url,
                prompt,
                room_type,
                style_preset
            )
            logger.info("Project update result: %s", success)
    except Exception as e:
        logger.error("Error creating GenerationJob: %s", str(e))
        raise
    
    return job.model_dump()  # type: ignore[attr-defined]


async def process_generation_job(job_id: str, max_retries: int = 3, timeout: int = 120) -> None:
    """
    Process a generation job with improved error handling and retry mechanism.
    
    Args:
        job_id: ID of the generation job to process
        max_retries: Maximum number of retry attempts for image generation
        timeout: Timeout in seconds for the Gemini API call
    """
    if db_client.prisma is None:
        await db_client.connect()
    job = await db_client.prisma.generationjob.find_unique(where={"id": job_id})  # type: ignore
    if not job:
        logger.warning(f"Job {job_id} not found, cannot process")
        return
        
    try:
        # Update job status to running
        start_time = time.time()
        await db_client.prisma.generationjob.update(  # type: ignore
            where={"id": job_id},
            data={"status": "running"},
        )
        db_update_time = time.time() - start_time
        logger.info(f"DB update to 'running' took {db_update_time:.3f}s for job {job_id}")

        # Use Google Gemini 2.5 Flash Image Preview with retry and timeout
        try:
            generation_start = time.time()
            out_bytes = await generate_image_with_gemini_flash(
                image_url=job.reference,  # type: ignore[attr-defined]
                prompt=_compose_prompt(job.prompt, job.room_type, job.style_preset),
                max_retries=max_retries,
                timeout=timeout,
            )
            generation_time = time.time() - generation_start
            logger.info(f"Image generation took {generation_time:.3f}s for job {job_id}")
            
            # Upload image output
            upload_start = time.time()
            output_url = upload_bytes(
                out_bytes,
                content_type="image/png",
                key_prefix="generations/output/",
                filename=f"{job_id}.png",
            )
            upload_time = time.time() - upload_start
            logger.info(f"S3 upload took {upload_time:.3f}s for job {job_id}")

            # Update job as completed
            db_update_start = time.time()
            await db_client.prisma.generationjob.update(  # type: ignore
                where={"id": job_id},
                data={"status": "done", "output": output_url},
            )
            db_update_time = time.time() - db_update_start
            logger.info(f"DB update to 'done' took {db_update_time:.3f}s for job {job_id}")
            
            # Deduct 1 credit from user if job is associated with a user
            if job.userId:  # type: ignore[attr-defined]
                credit_start = time.time()
                await db_client.prisma.user.update(  # type: ignore
                    where={"id": job.userId},  # type: ignore[attr-defined]
                    data={"credits": {"decrement": 1}},
                )
                credit_time = time.time() - credit_start
                logger.info(f"Credit deduction took {credit_time:.3f}s for job {job_id}")
                
            total_time = time.time() - start_time
            logger.info(f"Total processing time: {total_time:.3f}s for job {job_id}")
            logger.info(f"Time breakdown - Generation: {generation_time:.3f}s ({generation_time/total_time*100:.1f}%), " +
                       f"Upload: {upload_time:.3f}s ({upload_time/total_time*100:.1f}%), " +
                       f"DB updates: {db_update_time:.3f}s ({db_update_time/total_time*100:.1f}%)")
                
        except TimeoutError as e:
            logger.error(f"Timeout error processing job {job_id}: {str(e)}")
            await db_client.prisma.generationjob.update(  # type: ignore
                where={"id": job_id},
                data={"status": "failed", "error": f"Timeout error: {str(e)}"},
            )
            
        except ValueError as e:
            logger.error(f"Value error processing job {job_id}: {str(e)}")
            await db_client.prisma.generationjob.update(  # type: ignore
                where={"id": job_id},
                data={"status": "failed", "error": f"Generation error: {str(e)}"},
            )
            
    except Exception as e:
        logger.exception(f"Unexpected error processing job {job_id}: {str(e)}")
        raw_message = f"{type(e).__name__}: {str(e)}"
        # Truncate very long messages (e.g., embedded base64) to keep DB small
        error_message = (raw_message[:500] + "... [truncated]") if len(raw_message) > 500 else raw_message
        await db_client.prisma.generationjob.update(  # type: ignore
            where={"id": job_id},
            data={"status": "failed", "error": error_message},
        )

from typing import Optional, List

def _compose_prompt(
    text_input: Optional[str] = None,
    room_type: Optional[str] = None,
    style_preset: Optional[str] = None,
) -> str:
    """
    Generates a detailed prompt for AI image generation based on user inputs.
    Aims for a complete remodel while preserving the room's rigid structures.

    Returns:
        str: The complete, formatted prompt string for the AI model.
    """
    
    # Start with the base instruction to use the provided image
    prompt_parts: List[str] = []
    prompt_parts.append("Using the provided image of an interior space, ")
    prompt_parts.append("Generate a stunning, high-end, photorealistic interior design remodel.")


    if text_input:
        # If specific text_input is provided, integrate it directly
        if room_type:
            prompt_parts.append(f"specifically a {room_type}, ")
        if style_preset:
            prompt_parts.append(f"in a {style_preset} style, ")

        # prompt_parts.append("Completely **strip and replace** all furnishings, decor, flooring, wall surfaces, and lighting from the reference image. **Preserve the architectural integrity of the room, including all windows, doors, passages, and rigid structural elements.**")
        prompt_parts.append(f"make the following change: {text_input}.")
        prompt_parts.append(" Ensure the new elements integrate seamlessly with the existing environment.")
        
    else:
        # If no specific text_input, trigger a full, aggressive remodel.
        prompt_parts.append("Generate a stunning, high-end, photorealistic interior design remodel.")
        
        # This is the aggressive instruction to remodel everything except the core structures.
        prompt_parts.append("Completely **strip and replace** all furnishings, decor, flooring, wall surfaces, and lighting from the reference image. **Preserve the architectural integrity of the room, including all windows, doors, passages, and rigid structural elements.**")
        
        # Integrate room type and style into the remodel instruction
        if room_type:
            prompt_parts.append(f"Redesign this {room_type} ")
        else:
            prompt_parts.append(f"Redesign this space ")
        
        if style_preset:
            prompt_parts.append(f"in a {style_preset} style, ")
        else:
            # Default to the desired aesthetic if no style is given
            prompt_parts.append("to be exceptionally functional yet deeply personal. Create a profoundly calming, sophisticated atmosphere by using a curated selection of artisanal furniture, luxurious materials, and minimalist decor. ")

    
    prompt_parts.append("The final image should showcase impeccable attention to detail, cinematic lighting, and a magazine-quality aesthetic. All new elements should be harmonious and brand new, reflecting a complete transformation.")
        
    return " ".join(prompt_parts).strip()


def _compose_moodboard_prompt(
    reference_image_url: str,
    prompt: Optional[str] = None,
    style: Optional[str] = None,
    color_palette: Optional[str] = None,
) -> str:
    """
    Compose a prompt for generating a visual moodboard image.
    """
    prompt_parts = [
        "Create a beautiful, professional moodboard collage inspired by this reference image.",
        "The moodboard should include:",
        "- Color palette swatches extracted from the reference image",
        "- Texture samples and material inspirations",
        "- Furniture pieces and decor items that complement the style",
        "- Lighting fixtures and accessories",
        "- Pattern and fabric samples",
        "- Typography or design elements if relevant",
        "Arrange these elements in an aesthetically pleasing grid or collage layout.",
        "The overall composition should be clean, professional, and magazine-quality.",
    ]
    
    if style:
        prompt_parts.append(f"Focus on {style} style elements and aesthetics.")
    
    if color_palette:
        prompt_parts.append(f"Emphasize the {color_palette} color palette throughout the moodboard.")
    
    if prompt:
        prompt_parts.append(f"Additional requirements: {prompt}")
    
    prompt_parts.append("The final moodboard should be visually cohesive and inspiring for interior design.")
    
    return " ".join(prompt_parts)


async def _async_sleep(seconds: float) -> None:

    await asyncio.sleep(seconds)


# --- Google Gemini 2.0 Flash Image Generation ---
async def generate_image_with_gemini(
    image_url: str,
    prompt: str = "Remodel this interior space",
) -> bytes:
    """
    Generate image using Gemini 2.0 Flash Preview.
    Returns PNG bytes of the generated image.
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("API key is required")
    
    # Download input image
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(image_url)
        response.raise_for_status()
        image_data = base64.b64encode(response.content).decode()
    
    # API request
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent"
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/png", "data": image_data}}
            ]
        }],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
    }
    
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, params={"key": settings.GEMINI_API_KEY}, json=payload)
        response.raise_for_status()
        data = response.json()
    
    # Extract image from response
    try:
        parts = data["candidates"][0]["content"]["parts"]
        for part in parts:
            # Check for inline_data
            if "inline_data" in part and "data" in part["inline_data"]:
                image_b64 = part["inline_data"]["data"]
                return base64.b64decode(image_b64)
            # Check for inlineData (alternative format)
            elif "inlineData" in part and "data" in part["inlineData"]:
                image_b64 = part["inlineData"]["data"]
                return base64.b64decode(image_b64)
        
        raise KeyError("No image found in response")
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Failed to extract image from response: {e}")

# --- Google Gemini 2.5 Flash Image - Nano Banana ---
async def generate_image_with_gemini_flash(
    image_url: str,
    prompt: str,
    max_retries: int = 3,
    timeout: int = 120,
) -> bytes:
    """
    Generate image using Gemini 2.5 Flash Image.
    Returns PNG bytes of the generated image.
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("API key is required")

    # Create a temporary file to store the downloaded image
    temp_file = None
    
    try:
        logger.info(f"Starting image generation with Gemini Flash. Image URL.")
        
        # Acquire semaphore to limit concurrent requests
        async with _gemini_semaphore:
            # Download the image from URL
            async with aiohttp.ClientSession() as session:
                logger.debug(f"Downloading reference image from URL: {image_url[:20]}...")
                try:
                    async with session.get(image_url) as response:
                        if response.status != 200:
                            error_msg = f"Failed to download image: HTTP {response.status}"
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                        
                        # Create a temporary file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp:
                            temp_file = temp.name
                            image_data = await response.read()
                            temp.write(image_data)
                            logger.debug(f"Reference image downloaded successfully ({len(image_data)} bytes)")
                except aiohttp.ClientError as e:
                    error_msg = f"Network error downloading reference image: {str(e)}"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            
            # Initialize Gemini client
            logger.debug("Initializing Gemini client")
            logger.debug(f"Gemini API key: {settings.GEMINI_API_KEY}")

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            # client = genai.Client(api_key="AIzaSyBqjU_XIH3Ag01tKoMRgsr9HANG_n4PM6k")
            
            # Open the downloaded image
            try:
                image = Image.open(temp_file)
                logger.debug(f"Image opened successfully: {image.format} {image.size}")
            except Exception as e:
                error_msg = f"Failed to open downloaded image: {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Start the generation job
            logger.debug(f"Sending request to Gemini API with model: {settings.GEMINI_IMAGE_MODEL}")
            try:

                response = client.models.generate_content(
                    model=settings.GEMINI_IMAGE_MODEL,
                    contents=[image, prompt],
                )
                logger.debug("Received response from Gemini API")
            except Exception as e:
                error_msg = f"Gemini API request failed: {str(e)}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Log token usage
            if hasattr(response, 'usage_metadata') and hasattr(response.usage_metadata, 'total_token_count'):
                logger.info(f"Gemini token usage: {response.usage_metadata.total_token_count}")
            else:
                logger.warning("Could not determine Gemini token usage")

            # Extract image from response - simplified and optimized
            if hasattr(response, 'candidates') and response.candidates:
                logger.debug(f"Response has {len(response.candidates)} candidates")
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        # Direct binary data extraction - fastest method
                        logger.info("Successfully extracted image data from Gemini response")
                        return part.inline_data.data
                    else:
                        logger.debug(f"Part does not contain inline_data: {type(part)}")
            else:
                logger.error("Response does not contain any candidates")

            # If we get here, no image was found in the response
            logger.error("No image found in Gemini response")
            raise ValueError("No image found in Gemini response")   
            
    except Exception as e:
        logger.error(f"Error generating image with Gemini: {str(e)}")
        raise
    
    finally:
        # Clean up the temporary file
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)


# --- OpenAI Responses API Service ---
async def _call_openai_response(
    *,
    image_url: str,
    prompt: Optional[str],
    model: Optional[str] = None,
) -> str:
    """
    Minimal OpenAI Responses API call that accepts an image URL + prompt
    and returns response.output_text (text answer).

    Example usage mirrors the template you shared.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("OpenAI SDK not installed. Run: pip install openai") from e

    openai_client = OpenAI(api_key=api_key)

    resp = openai_client.responses.create(
        model=os.getenv("OPENAI_IMAGE_MODEL"),
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt or "Remodel this interior space"},
                {"type": "input_image", "image_url": image_url},
            ],
        }],
    )

    # responses.create returns a rich object; use convenience text
    return getattr(resp, "output_text", "")


# --- OpenAI Images Edit helper (minimal) ---
async def _call_openai_image_edit(
    *,
    image_url: str,
    prompt: Optional[str],
    width: int,
    height: int,
) -> bytes:
    """
    Minimal OpenAI Images Edit call. Downloads the input image and submits it
    to gpt-image-1 with the provided prompt. Returns PNG bytes.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError("OpenAI SDK not installed. Run: pip install openai") from e

    # Fetch input image bytes
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(image_url)
        r.raise_for_status()
        init_bytes = r.content

    client = OpenAI(api_key=api_key)

    # Provide image as file-like
    import io
    file_obj = io.BytesIO(init_bytes)
    file_obj.name = "reference.png"
    try:
        # OpenAI Python SDK v1 uses `images.edit` (singular), not `edits`
        resp = client.images.edit(
            model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1"),
            image=file_obj,
            prompt=prompt or "Remodel this interior space",
            size="1024x1024",
            # response_format="b64_json",
        )
    finally:
        file_obj.close()

    # Log token usage if available
    usage = getattr(resp, "usage", None)
    if usage:
        logger.info("OpenAI API usage - Total tokens: %s", getattr(usage, "total_tokens", "N/A"))
    else:
        logger.info("No usage information available in OpenAI response")

    data = getattr(resp, "data", None) or []
    if not data or not getattr(data[0], "b64_json", None):
        raise RuntimeError(f"OpenAI Images edit returned no image data: {resp}")

    return base64.b64decode(data[0].b64_json)


async def analyze_image_for_moodboard(
    reference_image_url: str,
    prompt: Optional[str] = None,
    style: Optional[str] = None,
    color_palette: Optional[str] = None,
) -> List[MoodboardItem]:
    """
    Use Gemini's vision model to analyze an image and generate moodboard items.
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("Gemini API key not configured")
    
    # Download image and encode to base64
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(reference_image_url)
        response.raise_for_status()
        image_data = base64.b64encode(response.content).decode()
    
    # Build analysis prompt
    analysis_prompt = f"""
    Analyze this interior design reference image and create a comprehensive moodboard with design recommendations.
    
    {f"Style preference: {style}" if style else ""}
    {f"Color palette preference: {color_palette}" if color_palette else ""}
    {f"Additional context: {prompt}" if prompt else ""}
    
    Please provide a detailed analysis in JSON format with the following structure:
    {{
        "items": [
            {{
                "title": "Item name",
                "description": "Detailed description",
                "category": "color|texture|furniture|lighting|decor|material",
                "hexColor": "#RRGGBB" (only for color items),
                "imageUrl": null
            }}
        ]
    }}
    
    Include 8-12 items covering:
    - 3-4 dominant colors from the image
    - 2-3 key textures or materials
    - 2-3 furniture pieces or design elements
    - 1-2 lighting suggestions
    - 1-2 decorative elements
    
    Focus on actionable design recommendations that capture the essence of this space.
    Return ONLY the JSON object, no additional text.
    """
    
    # API request with retry logic
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    
    payload = {
        "contents": [{
            "parts": [
                {"text": analysis_prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
            ]
        }]
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(url, params={"key": settings.GEMINI_API_KEY}, json=payload)
                response.raise_for_status()
                data = response.json()
                break
        except (httpx.WriteTimeout, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Gemini API timeout after {max_retries} attempts: {str(e)}")
            logger.warning(f"Gemini API timeout on attempt {attempt + 1}, retrying...")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    # Extract text response
    try:
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        logger.info(f"Gemini moodboard response: {content}")
        
        # Clean and parse JSON
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        try:
            parsed_data = json.loads(content)
            items_data = parsed_data.get("items", [])
        except json.JSONDecodeError:
            # Fallback: search for JSON pattern
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                parsed_data = json.loads(json_match.group())
                items_data = parsed_data.get("items", [])
            else:
                logger.error(f"No valid JSON found in response: {content}")
                items_data = []
        
        # Convert to MoodboardItem objects
        moodboard_items = []
        for item_data in items_data:
            try:
                item = MoodboardItem(
                    title=item_data.get("title", "Untitled"),
                    description=item_data.get("description", ""),
                    category=item_data.get("category", "decor"),
                    imageUrl=item_data.get("imageUrl"),
                    hexColor=item_data.get("hexColor")
                )
                moodboard_items.append(item)
            except Exception as e:
                logger.warning(f"Failed to create moodboard item: {e}")
                continue
        
        return moodboard_items
        
    except (KeyError, IndexError) as e:
        logger.error(f"Failed to extract text from Gemini response: {e}")
        raise RuntimeError(f"Failed to analyze image with Gemini: {str(e)}")


async def generate_moodboard(
    *,
    project_id: str,
    reference_image_url: str,
    prompt: Optional[str] = None,
    style: Optional[str] = None,
    color_palette: Optional[str] = None,
    user_id: Optional[str] = None,
) -> MoodboardOut:
    """
    Generate a visual moodboard image by analyzing a reference image and creating a collage-style moodboard.
    Uploads the generated moodboard image to S3 and stores metadata in database.
    """
    moodboard_id = str(uuid.uuid4())
    current_time = time.time()
    
    try:
        # Ensure database connection
        if db_client.prisma is None:
            await db_client.connect()
            
        # Create initial moodboard record
        await db_client.prisma.moodboard.create(data={
            "id": moodboard_id,
            "projectId": project_id,
            "userId": user_id,
            "referenceImage": reference_image_url,
            "prompt": prompt,
            "style": style,
            "colorPalette": color_palette,
            "status": "generating",
            "items": "[]",
        })
        
        # Generate visual moodboard image using Gemini
        moodboard_prompt = _compose_moodboard_prompt(
            reference_image_url=reference_image_url,
            prompt=prompt,
            style=style,
            color_palette=color_palette,
        )
        
        # Generate moodboard image using Gemini Flash
        moodboard_image_bytes = await generate_image_with_gemini_flash(
            image_url=reference_image_url,
            prompt=moodboard_prompt,
            max_retries=3,
            timeout=120,
        )
        
        # Upload moodboard image to S3
        moodboard_url = upload_bytes(
            moodboard_image_bytes,
            content_type="image/png",
            key_prefix="moodboards/",
            filename=f"{moodboard_id}.png",
        )
        
        # Analyze image for moodboard items (metadata)
        moodboard_items = await analyze_image_for_moodboard(
            reference_image_url=reference_image_url,
            prompt=prompt,
            style=style,
            color_palette=color_palette,
        )
        
        # Update moodboard with results
        items_json = json.dumps([item.dict() for item in moodboard_items])
        await db_client.prisma.moodboard.update(
            where={"id": moodboard_id},
            data={
                "status": "completed",
                "items": items_json,
                "output": moodboard_url,  # Store the S3 URL
            }
        )
        
        # Return MoodboardOut object
        return MoodboardOut(
            id=moodboard_id,
            projectId=project_id,
            userId=user_id or "",
            referenceImage=reference_image_url,
            prompt=prompt,
            style=style,
            colorPalette=color_palette,
            status="completed",
            items=moodboard_items,
            output=moodboard_url,  # Include the generated moodboard image URL
            createdAt=datetime.fromtimestamp(current_time),
            updatedAt=datetime.fromtimestamp(time.time()),
        )
        
    except Exception as e:
        logger.exception(f"Error generating moodboard: {e}")
        
        # Update status to failed
        try:
            await db_client.prisma.moodboard.update(
                where={"id": moodboard_id},
                data={
                    "status": "failed",
                }
            )
        except:
            pass
        
        raise RuntimeError(f"Failed to generate moodboard: {str(e)}")


async def get_project_moodboards(project_id: str) -> List[MoodboardOut]:
    """Get all moodboards for a project"""
    try:
        # Ensure database connection
        if db_client.prisma is None:
            await db_client.connect()
            
        moodboards = await db_client.prisma.moodboard.find_many(
            where={"projectId": project_id},
            order_by={"createdAt": "desc"}
        )
        
        result = []
        for mb in moodboards:
            try:
                items_data = json.loads(mb.items or "[]")
                items = [MoodboardItem(**item) for item in items_data]
            except:
                items = []
            
            result.append(MoodboardOut(
                id=mb.id,
                projectId=mb.projectId,
                userId=mb.userId or "",
                referenceImage=mb.referenceImage,
                prompt=mb.prompt,
                style=mb.style,
                colorPalette=mb.colorPalette,
                status=mb.status,
                items=items,
                output=mb.output,  # Include the generated moodboard image URL
                createdAt=mb.createdAt,
                updatedAt=mb.updatedAt,
            ))
        
        return result
        
    except Exception as e:
        logger.exception(f"Error fetching project moodboards: {e}")
        return []