import os
import hashlib
import redis
from dotenv import load_dotenv

load_dotenv()

ENVIRONMENT = os.environ.get("ENV", "development")
IN_MEMORY_CACHE={}

if ENVIRONMENT == "production":
    # redis_url = os.environ["REDIS_HOST"]
    redis_client = None

    # redis_client = redis.Redis(
    #     host= os.environ["REDIS_HOST"],
    #     port=os.environ["REDIS_PORT"],
    #     decode_responses=True,
    #     username="default",
    #     password=os.environ["REDIS_PASSWORD"],
    # )
else:
    redis_client = None


def generate_cache_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

def get_cached_response(key: str) -> str | None:
    hashed_key = generate_cache_key(key)
    if ENVIRONMENT == "production":
        # print("PRODUCTION")

        if not redis_client:
            return None
        cached = redis_client.get(hashed_key)
        if cached:
            return cached
    else:
        # print("DEVELOPMENT")
        return IN_MEMORY_CACHE.get(hashed_key)

def set_cached_response(key: str, value: str, ttl_seconds=3600):
    hashed_key = generate_cache_key(key)
    if ENVIRONMENT == "production":
        # print("PRODUCTION")
        if not redis_client:
            return None
        redis_client.setex(hashed_key, ttl_seconds, value)
    else:
        # print("DEVELOPMENT")
        IN_MEMORY_CACHE[hashed_key] = value
