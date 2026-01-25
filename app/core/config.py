from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from os import getenv, environ
<<<<<<< HEAD
import secrets
=======
>>>>>>> origin/master

load_dotenv(override=True)

class Settings(BaseSettings):
    APP_NAME: str = "Ventics AI API"
    VERSION: str = "0.1.0"
<<<<<<< HEAD
    ENVIRONMENT: str = getenv("ENVIRONMENT", "development")
    MODEL_PROVIDER: str = "stub"
    TIMEOUT: int = 30
    MAX_IMAGE_SIZE: int = 1024
    
    # Security settings
    JWT_SECRET_KEY: str = getenv("JWT_SECRET_KEY", "change-me-in-prod")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REQUIRE_EMAIL_VERIFICATION: bool = getenv("REQUIRE_EMAIL_VERIFICATION", "false").lower() in ("1", "true", "yes")
    
    # Password requirements
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    
    
    # CORS settings - stored as comma-separated string
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = getenv("RATE_LIMIT_ENABLED", "true").lower() in ("1", "true", "yes")
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = getenv("GOOGLE_CLIENT_ID")
=======
    MODEL_PROVIDER: str = "stub"
    TIMEOUT: int = 30
    MAX_IMAGE_SIZE: int = 1024
    # Auth settings
    JWT_SECRET_KEY: str = "change-me-in-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    GOOGLE_CLIENT_ID: str | None = None
>>>>>>> origin/master
    # Email settings
    SMTP_HOST: str | None = getenv("SMTP_HOST")
    SMTP_PORT: int = int(getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str | None = getenv("SMTP_USERNAME")
    SMTP_PASSWORD: str | None = getenv("SMTP_PASSWORD")
    SMTP_FROM_EMAIL: str | None = getenv("SMTP_FROM_EMAIL")
    # Mailgun settings
    MAILGUN_API_KEY: str | None = getenv("MAILGUN_API_KEY")
    MAILGUN_DOMAIN: str | None = getenv("MAILGUN_DOMAIN")
    MAILGUN_FROM_EMAIL: str | None = getenv("MAILGUN_FROM_EMAIL")
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
    # CloudFront CDN
    CLOUDFRONT_DOMAIN: str | None = getenv("CLOUDFRONT_DOMAIN")
    # Whether to set ACL public-read on uploaded objects (helpful for simple public CDN behavior)
    S3_PUBLIC_READ: bool = getenv("S3_PUBLIC_READ", "true").lower() in ("1", "true", "yes")
    # Whether to return presigned GET URLs for uploaded objects (good for buckets with ACLs disabled)
    S3_RETURN_PRESIGNED: bool = getenv("S3_RETURN_PRESIGNED", "false").lower() in ("1", "true", "yes")
    # Presigned URL expiry in seconds
    S3_SIGNED_URL_EXPIRY: int = int(getenv("S3_SIGNED_URL_EXPIRY", "86400"))

    # Google Gemini
    GEMINI_API_KEY: str | None = None
    GEMINI_IMAGE_MODEL: str = getenv("GEMINI_IMAGE_MODEL")
    
    # OpenAI
    OPENAI_API_KEY: str | None = getenv("OPENAI_API_KEY")
    OPENAI_IMAGE_MODEL: str = getenv("OPENAI_IMAGE_MODEL", "gpt-4o")

    # Paystack
    PAYSTACK_SECRET_KEY: str | None = getenv("PAYSTACK_SECRET_KEY")
    PAYSTACK_PUBLIC_KEY: str | None = getenv("PAYSTACK_PUBLIC_KEY")
<<<<<<< HEAD
    PAYSTACK_WEBHOOK_SECRET: str | None = getenv("PAYSTACK_WEBHOOK_SECRET")  # Required for webhook verification
=======
    PAYSTACK_WEBHOOK_SECRET: str | None = getenv("PAYSTACK_WEBHOOK_SECRET")
>>>>>>> origin/master
    REPLICATE_API_TOKEN: str | None = getenv("REPLICATE_API_TOKEN")
    
    # Bing Search API
    BING_SEARCH_API_KEY: str | None = getenv("BING_SEARCH_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
<<<<<<< HEAD
    
    def get_allowed_origins_list(self) -> list[str]:
        """Parse ALLOWED_ORIGINS string into list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    def validate_security_config(self) -> None:
        """Validate security-critical configuration on startup."""
        warnings = []
        errors = []
        
        # Check JWT secret
        if self.JWT_SECRET_KEY == "change-me-in-prod" and self.ENVIRONMENT == "production":
            errors.append("JWT_SECRET_KEY must be changed in production!")
        
        if len(self.JWT_SECRET_KEY) < 32:
            warnings.append("JWT_SECRET_KEY should be at least 32 characters long")
        
        # Check CORS
        if "*" in self.ALLOWED_ORIGINS and self.ENVIRONMENT == "production":
            errors.append("CORS allow_origins=['*'] is not allowed in production!")
        
        # Check Paystack webhook secret
        if self.PAYSTACK_SECRET_KEY and not self.PAYSTACK_WEBHOOK_SECRET:
            warnings.append("PAYSTACK_WEBHOOK_SECRET is not set - webhook signature verification disabled")
        
        # Print warnings
        for warning in warnings:
            print(f"WARNING: {warning}")
        
        # Raise errors
        if errors:
            error_msg = "\n".join(f"ERROR: {error}" for error in errors)
            raise ValueError(f"Security configuration errors:\n{error_msg}")


settings = Settings()

# Validate security configuration on import
if getenv("SKIP_CONFIG_VALIDATION") != "true":
    settings.validate_security_config()
=======


settings = Settings()
>>>>>>> origin/master
