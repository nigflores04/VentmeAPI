from __future__ import annotations

import uuid
from typing import List, Optional
import os

import httpx

from app.core.config import settings
from app.db import client as db_client
from app.services.storage_service import upload_bytes
from prisma import Json  # type: ignore
import logging

logger = logging.getLogger(__name__)


async def enqueue_remodel_job(
    *,
    image_bytes: bytes,
    content_type: str,
    prompt: Optional[str],
    style: Optional[str],
    items: Optional[List[str]],
    width: int,
    height: int,
    user_id: Optional[str] = None,
) -> dict:
    if not settings.S3_BUCKET:
        raise RuntimeError("S3 not configured")
    # Ensure DB connection (avoid stale imported reference)
    if db_client.prisma is None:
        await db_client.connect()

    # Cap size to MAX_IMAGE_SIZE
    width = min(width, settings.MAX_IMAGE_SIZE)
    height = min(height, settings.MAX_IMAGE_SIZE)

    # Upload input to S3
    input_url = upload_bytes(
        image_bytes,
        content_type=content_type,
        key_prefix="remodels/input/",
        filename=f"{uuid.uuid4()}.png",
    )

    # Create job in DB (use relation connect for user; omit optional JSON when None)
    data: dict = {
        "status": "queued",
        "inputImageUrl": input_url,
        "prompt": prompt,
        "style": style,
        "width": width,
        "height": height,
    }
    if items:
        # Only include when non-empty; wrap in Prisma Json to satisfy input type
        data["items"] = Json(items)
    if user_id:
        data["user"] = {"connect": {"id": user_id}}

    logger.info("Creating RemodelJob with data keys=%s", list(data.keys()))
    job = await db_client.prisma.remodeljob.create(  # type: ignore
        data=data
    )
    return job.model_dump()  # type: ignore[attr-defined]


async def process_job(job_id: str) -> None:
    if db_client.prisma is None:
        await db_client.connect()
    job = await db_client.prisma.remodeljob.find_unique(where={"id": job_id})  # type: ignore
    if not job:
        return
    try:
        await db_client.prisma.remodeljob.update(  # type: ignore
            where={"id": job_id},
            data={"status": "running"},
        )

        # Use OpenAI Images API to generate an edited image from the input image + prompt
        out_bytes = await _call_openai_image_edit(
            image_url=job.inputImageUrl,  # type: ignore[attr-defined]
            prompt=job.prompt,
            width=job.width,  # type: ignore[attr-defined]
            height=job.height,  # type: ignore[attr-defined]
        )

        # Upload image output
        output_url = upload_bytes(
            out_bytes,
            content_type="image/png",
            key_prefix="remodels/output/",
            filename=f"{job_id}.png",
        )

        await db_client.prisma.remodeljob.update(  # type: ignore
            where={"id": job_id},
            data={"status": "done", "outputImageUrl": output_url},
        )
    except Exception as e:
        await db_client.prisma.remodeljob.update(  # type: ignore
            where={"id": job_id},
            data={"status": "failed", "error": str(e)},
        )

def _build_firefly_payload(
    *,
    prompt: Optional[str],
    image_url: str,
    width: int,
    height: int,
    style: Optional[str],
    items: Optional[List[str]],
) -> dict:
    # Merge style and items into prompt if needed
    parts: List[str] = []
    if prompt:
        parts.append(prompt)
    if style:
        parts.append(f"style: {style}")
    if items:
        parts.append("items: " + ", ".join(items))
    final_prompt = ". ".join(parts) or "interior design remodel"

    payload: dict = {
        "contentClass": "photo",
        "numVariations": 1,
        "prompt": final_prompt,
        "size": {"height": int(height), "width": int(width)},
        "structure": {
            "imageReference": {
                "source": {
                    "url": image_url
                }
            },
            "strength": 100,
        },
        "upsamplerType": "default",
        "visualIntensity": 2,
    }

    # Optionally include style presets if `style` is provided (as preset keyword)
    if style:
        payload["style"] = {
            "imageReference": {"source": {}},
            "presets": [style],
            "strength": 100,
        }

    return payload


async def _call_firefly(
    *,
    image_url: str,
    prompt: Optional[str],
    style: Optional[str],
    items: Optional[List[str]],
    width: int,
    height: int,
) -> bytes:
    """
    Minimal Firefly flow:
    1) POST /v3/images/generate-async
    2) Poll GET /v3/status/{jobId}
    3) On "succeeded", download result.outputs[0].image.url
    """
    api_key = getattr(settings, "ADOBE_API_KEY", None)
    access_token = getattr(settings, "ADOBE_ACCESS_TOKEN", None)
    model_version = getattr(settings, "ADOBE_MODEL_VERSION", "image3")

    if not api_key or not access_token:
        # Fallback: return original image when Firefly not configured
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(image_url)
            r.raise_for_status()
            return r.content

    gen_url = "https://firefly-api.adobe.io/v3/images/generate-async"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "x-api-key": api_key,
        "x-model-version": model_version,
        "Content-Type": "application/json",
    }

    # Build minimal payload using your spec
    payload = _build_firefly_payload(
        prompt=_compose_prompt(prompt, style, items),
        image_url=image_url,
        width=width,
        height=height,
        style=style,
        items=None,  # keep payload simple; items already merged into prompt
    )

    async with httpx.AsyncClient(timeout=120) as client:
        # 1) Kick off async generation
        try:
            resp = await client.post(gen_url, headers=headers, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            body = e.response.text if e.response is not None else str(e)
            raise RuntimeError(f"Firefly generate-async error {e.response.status_code if e.response else ''}: {body}") from e

        gen_data = resp.json()
        job_id = gen_data.get("jobId")
        status_url = gen_data.get("statusUrl")
        if not job_id and not status_url:
            raise RuntimeError(f"Unexpected Firefly response: {gen_data}")

        # 2) Poll job status
        status_endpoint = status_url or f"https://firefly-api.adobe.io/v3/status/{job_id}"
        while True:
            s = await client.get(status_endpoint, headers={"Authorization": f"Bearer {access_token}", "x-api-key": api_key})
            s.raise_for_status()
            s_json = s.json()
            status = str(s_json.get("status", "")).lower()
            if status == "succeeded":
                outputs = ((s_json.get("result") or {}).get("outputs") or [])
                if not outputs:
                    raise RuntimeError(f"Firefly succeeded but no outputs: {s_json}")
                img = outputs[0].get("image") or {}
                img_url = img.get("url")
                if not img_url:
                    raise RuntimeError(f"Firefly succeeded but no image url: {s_json}")
                file_resp = await client.get(img_url)
                file_resp.raise_for_status()
                return file_resp.content
            if status in {"failed", "timeout"}:
                raise RuntimeError(f"Firefly job {status}: {s_json}")
            # running/queued
            await _async_sleep(2.0)


def _compose_prompt(prompt: Optional[str], style: Optional[str], items: Optional[List[str]]) -> str:
    parts: List[str] = []
    if prompt:
        parts.append(prompt)
    if style:
        parts.append(f"style: {style}")
    if items:
        parts.append("items: " + ", ".join(items))
    return ". ".join(parts) or "interior design remodel"


async def _async_sleep(seconds: float) -> None:
    import asyncio as _asyncio
    await _asyncio.sleep(seconds)


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
    import io, base64
    file_obj = io.BytesIO(init_bytes)
    file_obj.name = "init.png"
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

    data = getattr(resp, "data", None) or []
    if not data or not getattr(data[0], "b64_json", None):
        raise RuntimeError(f"OpenAI Images edit returned no image data: {resp}")

    return base64.b64decode(data[0].b64_json)