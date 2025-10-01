"""
Environment-specific configuration templates for different deployment scenarios.

This module provides pre-configured settings for development, staging, and production
environments with appropriate security and performance optimizations for each.
"""

import secrets
from pathlib import Path
from typing import Dict, Any

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class BaseEnvironmentSettings(BaseSettings):
    """Base settings shared across all environments"""

    # Project info
    PROJECT_NAME: str = "FileManager Telegram Bot"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Secure remote Android device control and file management bot"

    # Bot Configuration (will be overridden by specific env)
    BOT_TOKEN: str = Field(..., description="Telegram bot token")
    BOT_WEBHOOK_URL: str | None = Field(None, description="Webhook URL for production")
    BOT_WEBHOOK_PATH: str = Field("/webhook", description="Webhook path")

    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ENCRYPTION_KEY: str = Field(default_factory=lambda: secrets.token_hex(32))

    # RSA Keys
    RSA_PRIVATE_KEY_PATH: str = Field("keys/private.pem")
    RSA_PUBLIC_KEY_PATH: str = Field("keys/public.pem")

    # File handling
    MAX_FILE_SIZE: int = Field(50 * 1024 * 1024, description="Max file size in bytes")
    UPLOAD_DIR: str = Field("uploads", description="Upload directory")
    TEMP_DIR: str = Field("temp", description="Temporary files directory")

    # Device communication
    DEVICE_TIMEOUT: int = Field(30, description="Device timeout in seconds")
    MAX_CONNECTIONS_PER_USER: int = Field(3, description="Max connections per user")
    MAX_DEVICES_PER_USER: int = Field(5, description="Max devices per user")

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = Field(60, description="Requests per window")
    RATE_LIMIT_WINDOW: int = Field(60, description="Rate limit window in seconds")

    # Admin configuration
    ADMIN_USER_IDS: list[int] = Field(default_factory=list, description="Admin user IDs")

    # Environment
    ENVIRONMENT: str = Field("development", description="Environment name")

    @validator("ADMIN_USER_IDS", pre=True)
    def parse_admin_user_ids(cls, v):
        """Parse admin user IDs from environment"""
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    class Config:
        """Pydantic configuration"""
        case_sensitive = False


class DevelopmentSettings(BaseEnvironmentSettings):
    """Development environment settings"""

    ENVIRONMENT: str = "development"

    # Database - Local PostgreSQL
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://filemanager_dev:dev_password@localhost:5432/filemanager_dev",
        description="Development database URL"
    )

    # Redis - Local instance
    REDIS_URL: str = Field(
        "redis://localhost:6379/0",
        description="Development Redis URL"
    )

    # Logging - Verbose for debugging
    LOG_LEVEL: str = Field("DEBUG", description="Log level")
    LOG_FORMAT: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
        description="Log format"
    )

    # API - Local development
    API_HOST: str = Field("localhost", description="API host")
    API_PORT: int = Field(8000, description="API port")

    # WebSocket - Development settings
    WS_HEARTBEAT_INTERVAL: int = Field(30, description="WebSocket heartbeat")
    WS_TIMEOUT: int = Field(60, description="WebSocket timeout")

    # Debug settings
    DEBUG: bool = Field(True, description="Debug mode")
    RELOAD: bool = Field(True, description="Auto reload")

    # Development-specific limits (more permissive)
    MAX_FILE_SIZE: int = Field(100 * 1024 * 1024, description="Max file size (100MB for dev)")
    RATE_LIMIT_REQUESTS: int = Field(120, description="More permissive rate limiting")
    DEVICE_TIMEOUT: int = Field(60, description="Longer timeout for debugging")


class StagingSettings(BaseEnvironmentSettings):
    """Staging environment settings"""

    ENVIRONMENT: str = "staging"

    # Database - Staging PostgreSQL (could be remote)
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://filemanager_staging:staging_password@localhost:5432/filemanager_staging",
        description="Staging database URL"
    )

    # Redis - Staging instance
    REDIS_URL: str = Field(
        "redis://localhost:6379/1",
        description="Staging Redis URL"
    )

    # Logging - Balanced verbosity
    LOG_LEVEL: str = Field("INFO", description="Log level")
    LOG_FORMAT: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )

    # API - Staging server
    API_HOST: str = Field("0.0.0.0", description="API host")
    API_PORT: int = Field(8000, description="API port")

    # WebSocket - Staging settings
    WS_HEARTBEAT_INTERVAL: int = Field(30, description="WebSocket heartbeat")
    WS_TIMEOUT: int = Field(60, description="WebSocket timeout")

    # Staging settings
    DEBUG: bool = Field(False, description="Debug mode")
    RELOAD: bool = Field(False, description="Auto reload")

    # Staging-specific limits (moderate)
    MAX_FILE_SIZE: int = Field(75 * 1024 * 1024, description="Max file size (75MB for staging)")
    RATE_LIMIT_REQUESTS: int = Field(90, description="Moderate rate limiting")
    DEVICE_TIMEOUT: int = Field(45, description="Moderate timeout")


class ProductionSettings(BaseEnvironmentSettings):
    """Production environment settings"""

    ENVIRONMENT: str = "production"

    # Database - Production PostgreSQL (remote, managed)
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://filemanager_prod:prod_password@localhost:5432/filemanager_prod",
        description="Production database URL"
    )

    # Redis - Production instance (separate database)
    REDIS_URL: str = Field(
        "redis://localhost:6379/2",
        description="Production Redis URL"
    )

    # Logging - Production optimized
    LOG_LEVEL: str = Field("WARNING", description="Log level")
    LOG_FORMAT: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )

    # API - Production server
    API_HOST: str = Field("0.0.0.0", description="API host")
    API_PORT: int = Field(8000, description="API port")

    # WebSocket - Production settings
    WS_HEARTBEAT_INTERVAL: int = Field(20, description="WebSocket heartbeat")
    WS_TIMEOUT: int = Field(40, description="WebSocket timeout")

    # Production settings
    DEBUG: bool = Field(False, description="Debug mode")
    RELOAD: bool = Field(False, description="Auto reload")

    # Production-specific limits (strict)
    MAX_FILE_SIZE: int = Field(50 * 1024 * 1024, description="Max file size (50MB for production)")
    RATE_LIMIT_REQUESTS: int = Field(60, description="Strict rate limiting")
    DEVICE_TIMEOUT: int = Field(30, description="Strict timeout")

    # Production security
    ENABLE_WEBHOOK: bool = Field(True, description="Enable webhook")
    SSL_CERT_PATH: str | None = Field(None, description="SSL certificate path")
    SSL_KEY_PATH: str | None = Field(None, description="SSL private key path")

    # Monitoring and health checks
    HEALTH_CHECK_INTERVAL: int = Field(30, description="Health check interval")
    METRICS_ENABLED: bool = Field(True, description="Enable metrics collection")


# Environment settings factory
def get_environment_settings(environment: str | None = None) -> BaseEnvironmentSettings:
    """Get settings for specific environment"""
    if environment == "production":
        return ProductionSettings()
    elif environment == "staging":
        return StagingSettings()
    else:
        return DevelopmentSettings()


# Configuration templates for different deployment scenarios
ENVIRONMENT_TEMPLATES = {
    "development": {
        "description": "Local development environment",
        "database": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "filemanager_dev",
            "username": "filemanager_dev",
            "password": "dev_password",
            "docker_compose": True
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "database": 0,
            "docker_compose": True
        },
        "logging": {
            "level": "DEBUG",
            "file": "logs/dev.log",
            "max_size": "10MB",
            "backup_count": 5
        },
        "performance": {
            "debug": True,
            "reload": True,
            "workers": 1,
            "timeout": 60
        }
    },

    "staging": {
        "description": "Staging environment for testing",
        "database": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "filemanager_staging",
            "username": "filemanager_staging",
            "password": "staging_password",
            "docker_compose": True,
            "ssl_mode": "require"
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "database": 1,
            "docker_compose": True,
            "ssl": True
        },
        "logging": {
            "level": "INFO",
            "file": "logs/staging.log",
            "max_size": "50MB",
            "backup_count": 10
        },
        "performance": {
            "debug": False,
            "reload": False,
            "workers": 2,
            "timeout": 45
        }
    },

    "production": {
        "description": "Production environment",
        "database": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database": "filemanager_prod",
            "username": "filemanager_prod",
            "password": "prod_password",
            "docker_compose": True,
            "ssl_mode": "require",
            "connection_pool": {
                "min_size": 5,
                "max_size": 20
            }
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "database": 2,
            "docker_compose": True,
            "ssl": True,
            "cluster": False,
            "connection_pool": {
                "max_connections": 20
            }
        },
        "logging": {
            "level": "WARNING",
            "file": "logs/prod.log",
            "max_size": "100MB",
            "backup_count": 30,
            "external": ["sentry", "logstash"]
        },
        "performance": {
            "debug": False,
            "reload": False,
            "workers": 4,
            "timeout": 30,
            "rate_limiting": True,
            "caching": True
        },
        "security": {
            "ssl": True,
            "webhook": True,
            "monitoring": True,
            "backup": True,
            "audit_logging": True
        }
    }
}


def generate_env_file_content(settings_class: type[BaseEnvironmentSettings]) -> str:
    """Generate .env file content for a settings class"""
    settings = settings_class()

    content = f"""# {settings.PROJECT_NAME} - {settings.ENVIRONMENT.title()} Environment
# Generated on: {__import__('datetime').datetime.now().isoformat()}
# Description: {ENVIRONMENT_TEMPLATES[settings.ENVIRONMENT]['description']}

# =============================================================================
# BOT CONFIGURATION
# =============================================================================
BOT_TOKEN=your_bot_token_here
BOT_WEBHOOK_URL=https://your-domain.com
BOT_WEBHOOK_PATH=/webhook

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
DATABASE_URL={settings.DATABASE_URL}

# =============================================================================
# REDIS CONFIGURATION
# =============================================================================
REDIS_URL={settings.REDIS_URL}

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================
SECRET_KEY={settings.SECRET_KEY}
ENCRYPTION_KEY={settings.ENCRYPTION_KEY}
RSA_PRIVATE_KEY_PATH={settings.RSA_PRIVATE_KEY_PATH}
RSA_PUBLIC_KEY_PATH={settings.RSA_PUBLIC_KEY_PATH}

# =============================================================================
# FILE UPLOAD CONFIGURATION
# =============================================================================
MAX_FILE_SIZE={settings.MAX_FILE_SIZE}
UPLOAD_DIR={settings.UPLOAD_DIR}
TEMP_DIR={settings.TEMP_DIR}

# =============================================================================
# DEVICE COMMUNICATION
# =============================================================================
DEVICE_TIMEOUT={settings.DEVICE_TIMEOUT}
MAX_CONNECTIONS_PER_USER={settings.MAX_CONNECTIONS_PER_USER}
MAX_DEVICES_PER_USER={settings.MAX_DEVICES_PER_USER}

# =============================================================================
# RATE LIMITING
# =============================================================================
RATE_LIMIT_REQUESTS={settings.RATE_LIMIT_REQUESTS}
RATE_LIMIT_WINDOW={settings.RATE_LIMIT_WINDOW}

# =============================================================================
# API CONFIGURATION
# =============================================================================
API_HOST={settings.API_HOST}
API_PORT={settings.API_PORT}

# =============================================================================
# WEBSOCKET CONFIGURATION
# =============================================================================
WS_HEARTBEAT_INTERVAL={settings.WS_HEARTBEAT_INTERVAL}
WS_TIMEOUT={settings.WS_TIMEOUT}

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
LOG_LEVEL={settings.LOG_LEVEL}
LOG_FORMAT={settings.LOG_FORMAT.replace('%', '%%')}

# =============================================================================
# ADMIN CONFIGURATION
# =============================================================================
ADMIN_USER_IDS={','.join(map(str, settings.ADMIN_USER_IDS))}

# =============================================================================
# ENVIRONMENT CONFIGURATION
# =============================================================================
ENVIRONMENT={settings.ENVIRONMENT}
DEBUG={str(settings.DEBUG)}
RELOAD={str(settings.RELOAD)}

"""

    # Add production-specific settings
    if settings.ENVIRONMENT == "production":
        content += """
# =============================================================================
# PRODUCTION SECURITY
# =============================================================================
ENABLE_WEBHOOK=true
SSL_CERT_PATH=/etc/ssl/certs/bot.crt
SSL_KEY_PATH=/etc/ssl/private/bot.key
HEALTH_CHECK_INTERVAL=30
METRICS_ENABLED=true

"""

    # Add Docker Compose specific settings
    content += """
# =============================================================================
# DOCKER COMPOSE (Local Development)
# =============================================================================
POSTGRES_PASSWORD=your-postgres-password-here
COMPOSE_PROJECT_NAME=filemanager-bot-{settings.ENVIRONMENT}
"""

    return content


def create_environment_config_files(output_dir: Path | None = None) -> Dict[str, Path]:
    """Create .env files for all environments"""
    if output_dir is None:
        output_dir = Path(__file__).parent.parent

    created_files = {}

    for env_name in ["development", "staging", "production"]:
        env_file = output_dir / f".env.{env_name}"

        if env_name == "development":
            settings_class = DevelopmentSettings
        elif env_name == "staging":
            settings_class = StagingSettings
        else:
            settings_class = ProductionSettings

        content = generate_env_file_content(settings_class)

        with open(env_file, "w", encoding="utf-8") as f:
            f.write(content)

        created_files[env_name] = env_file
        print(f"✅ Created {env_file}")

    # Create default .env file (development)
    default_env = output_dir / ".env"
    if not default_env.exists():
        import shutil
        shutil.copy(output_dir / ".env.development", default_env)
        print(f"✅ Created default {default_env}")

    return created_files


if __name__ == "__main__":
    """Generate environment configuration files"""
    print("🔧 Generating environment configuration files...")

    try:
        files = create_environment_config_files()
        print(f"\n✅ Successfully created {len(files)} environment configuration files:")
        for env, path in files.items():
            print(f"  • {env}: {path}")

        print("\n📝 Next steps:")
        print("1. Edit each .env file with your specific values")
        print("2. Set BOT_TOKEN for each environment")
        print("3. Configure database credentials")
        print("4. Update domain names for webhook URLs")

    except Exception as e:
        print(f"❌ Error creating configuration files: {e}")
        exit(1)