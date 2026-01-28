from urllib.parse import urlparse
from app.core.config import settings


def build_cloudfront_url(s3_url: str) -> str:
    """
    Convert S3 URL to CloudFront URL.
    Simple replacement - no signing needed if CloudFront is public.
    """
    if not settings.CLOUDFRONT_DOMAIN:
        return s3_url
    
    # Extract object key from S3 URL
    parsed = urlparse(s3_url)
    object_key = parsed.path.lstrip('/')
    
    # Handle bucket name in path
    if settings.S3_BUCKET and object_key.startswith(settings.S3_BUCKET + '/'):
        object_key = object_key[len(settings.S3_BUCKET) + 1:]
    
    return f"https://{settings.CLOUDFRONT_DOMAIN}/{object_key}"
