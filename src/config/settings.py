"""
Application settings and configuration
"""

import secrets
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Bot Configuration
    BOT_TOKEN: str = Field(..., env="BOT_TOKEN", description="Telegram bot token")
    BOT_WEBHOOK_URL: Optional[str] = Field(None, env="BOT_WEBHOOK_URL")
    BOT_WEBHOOK_PATH: str = Field("/webhook", env="BOT_WEBHOOK_PATH")

    # Database Configuration
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://user:password@localhost/filemanager",
        env="DATABASE_URL",
        description="PostgreSQL connection URL"
    )

    # Redis Configuration
    REDIS_URL: str = Field(
        "redis://localhost:6379",
        env="REDIS_URL",
        description="Redis connection URL"
    )

    # Security Configuration
    SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        env="SECRET_KEY",
        description="Application secret key"
    )
    ENCRYPTION_KEY: str = Field(
        default_factory=lambda: secrets.token_hex(32),
        env="ENCRYPTION_KEY",
        description="Encryption key for sensitive data"
    )

    # RSA Key Configuration
    RSA_PRIVATE_KEY_PATH: str = Field(
        "keys/private.pem",
        env="RSA_PRIVATE_KEY_PATH"
    )
    RSA_PUBLIC_KEY_PATH: str = Field(
        "keys/public.pem",
        env="RSA_PUBLIC_KEY_PATH"
    )

    # File Upload Configuration
    MAX_FILE_SIZE: int = Field(
        50 * 1024 * 1024,  # 50MB
        env="MAX_FILE_SIZE",
        description="Maximum file size for uploads in bytes"
    )
    UPLOAD_DIR: str = Field(
        "uploads",
        env="UPLOAD_DIR",
        description="Directory for temporary file uploads"
    )

    # Device Communication
    DEVICE_TIMEOUT: int = Field(
        30,
        env="DEVICE_TIMEOUT",
        description="Timeout for device communication in seconds"
    )
    MAX_CONNECTIONS_PER_USER: int = Field(
        3,
        env="MAX_CONNECTIONS_PER_USER",
        description="Maximum concurrent connections per user"
    )

    # WebSocket Configuration
    WS_HEARTBEAT_INTERVAL: int = Field(
        30,
        env="WS_HEARTBEAT_INTERVAL",
        description="WebSocket heartbeat interval in seconds"
    )
    WS_TIMEOUT: int = Field(
        60,
        env="WS_TIMEOUT",
        description="WebSocket timeout in seconds"
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(
        "INFO",
        env="LOG_LEVEL",
        description="Logging level"
    )
    LOG_FORMAT: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )

    # Admin Configuration
    ADMIN_USER_IDS: List[int] = Field(
        default_factory=list,
        env="ADMIN_USER_IDS",
        description="List of admin user IDs"
    )

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(
        60,
        env="RATE_LIMIT_REQUESTS",
        description="Number of requests allowed per time window"
    )
    RATE_LIMIT_WINDOW: int = Field(
        60,
        env="RATE_LIMIT_WINDOW",
        description="Rate limit time window in seconds"
    )

    # API Configuration
    API_HOST: str = Field(
        "0.0.0.0",
        env="API_HOST",
        description="API host address"
    )
    API_PORT: int = Field(
        8000,
        env="API_PORT",
        description="API port"
    )

    # WebSocket Configuration
    WS_HOST: str = Field(
        "0.0.0.0",
        env="WS_HOST",
        description="WebSocket host address"
    )
    WS_PORT: int = Field(
        8765,
        env="WS_PORT",
        description="WebSocket port"
    )

    # Environment
    ENVIRONMENT: str = Field(
        "development",
        env="ENVIRONMENT",
        description="Application environment"
    )

    @validator("ADMIN_USER_IDS", pre=True)
    def parse_admin_user_ids(cls, v):
        """Parse admin user IDs from environment variable"""
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment setting"""
        if v not in ["development", "staging", "production"]:
            raise ValueError("Environment must be development, staging, or production")
        return v

    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()