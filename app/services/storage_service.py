from __future__ import annotations

import uuid
from typing import Optional
import logging

import boto3
from botocore.client import Config

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_s3_client():
    if not settings.S3_ACCESS_KEY_ID or not settings.S3_SECRET_ACCESS_KEY:
        raise RuntimeError("S3 credentials not configured")
    session = boto3.session.Session()
    client = session.client(
        "s3",
        region_name=settings.S3_REGION,
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
    )
    return client


def upload_bytes(
    data: bytes,
    *,
    content_type: str,
    key_prefix: str = "uploads/",
    filename: Optional[str] = None,
) -> str:
    """Upload bytes to S3 and return a URL.

    The bucket is taken from settings.S3_BUCKET. The key is key_prefix + filename or a UUID.
    """
    if not settings.S3_BUCKET:
        raise RuntimeError("S3_BUCKET not configured")
    client = _get_s3_client()

    if not filename:
        filename = str(uuid.uuid4())
    key = f"{key_prefix}{filename}"

    # Upload object without ACL to support buckets with Object Ownership 'bucket owner enforced'
    client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
    )

    # If requested, try to set ACL via a separate call; ignore if bucket disallows ACLs
    if getattr(settings, "S3_PUBLIC_READ", False):
        try:
            client.put_object_acl(Bucket=settings.S3_BUCKET, Key=key, ACL="public-read")
        except Exception as acl_err:  # pragma: no cover
            logger.info("Skipping ACL public-read on %s: %s", key, str(acl_err))

    # Build a public URL (assumes object is publicly readable)
    if settings.S3_ENDPOINT_URL:
        base = settings.S3_ENDPOINT_URL.rstrip("/")
        return f"{base}/{settings.S3_BUCKET}/{key}"
    elif settings.S3_REGION:
        return f"https://{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com/{key}"
    else:
        return f"https://{settings.S3_BUCKET}.s3.amazonaws.com/{key}"
