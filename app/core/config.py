from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from os import getenv

load_dotenv()

class Settings(BaseSettings):
    APP_NAME: str = "Ventics AI API"
    VERSION: str = "0.1.0"
    MODEL_PROVIDER: str = "stub"
    TIMEOUT: int = 30
    MAX_IMAGE_SIZE: int = 1024
    # Auth settings
    JWT_SECRET_KEY: str = "change-me-in-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GOOGLE_CLIENT_ID: str | None = None
    # Email settings
    SMTP_HOST: str | None = getenv("SMTP_HOST")
    SMTP_PORT: int = int(getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str | None = getenv("SMTP_USERNAME")
    SMTP_PASSWORD: str | None = getenv("SMTP_PASSWORD")
    SMTP_FROM_EMAIL: str | None = getenv("SMTP_FROM_EMAIL")
    # Database
    DATABASE_URL: str | None = getenv("DATABASE_URL")

    # Stability AI
    STABILITY_API_KEY: str | None = getenv("STABILITY_API_KEY")
    STABILITY_ENGINE_ID: str = getenv("STABILITY_ENGINE_ID")
    # S3
    S3_BUCKET: str | None = getenv("S3_BUCKET")
    S3_REGION: str | None = getenv("S3_REGION")
    S3_ACCESS_KEY_ID: str | None = getenv("S3_ACCESS_KEY_ID")
    S3_SECRET_ACCESS_KEY: str | None = getenv("S3_SECRET_ACCESS_KEY")
    S3_ENDPOINT_URL: str | None = getenv("S3_ENDPOINT_URL")
    # Whether to set ACL public-read on uploaded objects (helpful for simple public CDN behavior)
    S3_PUBLIC_READ: bool = getenv("S3_PUBLIC_READ", "true").lower() in ("1", "true", "yes")
    # Whether to return presigned GET URLs for uploaded objects (good for buckets with ACLs disabled)
    S3_RETURN_PRESIGNED: bool = getenv("S3_RETURN_PRESIGNED", "true").lower() in ("1", "true", "yes")
    # Presigned URL expiry in seconds
    S3_SIGNED_URL_EXPIRY: int = int(getenv("S3_SIGNED_URL_EXPIRY", "86400"))

    # Google Gemini
    GEMINI_API_KEY: str | None = getenv("GEMINI_API_KEY")
    GEMINI_IMAGE_MODEL: str = getenv("GEMINI_IMAGE_MODEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
