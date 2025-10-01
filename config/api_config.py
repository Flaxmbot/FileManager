"""
Telegram Bot API Configuration and Integration Setup

This module provides comprehensive API configuration for Telegram Bot API integration,
including rate limiting, retry policies, webhook handling, and security configurations.

Features:
- API endpoint configuration
- Rate limiting and throttling
- Retry policies and error handling
- Webhook security validation
- Request/response middleware
- Health monitoring integration
"""

import asyncio
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

import httpx
from pydantic import BaseModel, Field, validator
import structlog


# API Configuration Models
class APIEndpoints(BaseModel):
    """Telegram Bot API endpoints configuration"""

    base_url: str = "https://api.telegram.org"
    file_base_url: str = "https://api.telegram.org/file"
    webhook_base_url: str = "https://api.telegram.org/bot{token}"

    # Rate limiting endpoints
    get_me: str = "/bot{token}/getMe"
    send_message: str = "/bot{token}/sendMessage"
    edit_message: str = "/bot{token}/editMessageText"
    delete_message: str = "/bot{token}/deleteMessage"
    send_photo: str = "/bot{token}/sendPhoto"
    send_document: str = "/bot{token}/sendDocument"
    send_audio: str = "/bot{token}/sendAudio"
    send_video: str = "/bot{token}/sendVideo"
    send_voice: str = "/bot{token}/sendVoice"

    # Webhook endpoints
    set_webhook: str = "/bot{token}/setWebhook"
    delete_webhook: str = "/bot{token}/deleteWebhook"
    get_webhook_info: str = "/bot{token}/getWebhookInfo"

    # File and media endpoints
    get_file: str = "/bot{token}/getFile"
    download_file: str = "/file/bot{token}/{file_path}"

    # Game and inline endpoints
    answer_callback_query: str = "/bot{token}/answerCallbackQuery"
    answer_inline_query: str = "/bot{token}/answerInlineQuery"

    # Admin endpoints
    get_chat_member: str = "/bot{token}/getChatMember"
    ban_chat_member: str = "/bot{token}/banChatMember"
    unban_chat_member: str = "/bot{token}/unbanChatMember"


class RateLimitConfig(BaseModel):
    """Rate limiting configuration"""

    requests_per_second: int = Field(30, description="Requests per second limit")
    requests_per_minute: int = Field(1000, description="Requests per minute limit")
    burst_limit: int = Field(50, description="Burst request limit")

    # Backoff configuration
    backoff_factor: float = Field(0.5, description="Exponential backoff factor")
    max_backoff_seconds: int = Field(60, description="Maximum backoff time")

    # Retry configuration
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_on_status_codes: List[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504],
        description="HTTP status codes to retry on"
    )


class SecurityConfig(BaseModel):
    """Security configuration for API"""

    validate_webhook_data: bool = Field(True, description="Validate webhook data integrity")
    validate_ssl_certificate: bool = Field(True, description="Validate SSL certificates")
    enable_request_signing: bool = Field(False, description="Enable request signing")

    # Webhook security
    webhook_secret_token: Optional[str] = Field(None, description="Webhook secret token")
    allowed_ips: List[str] = Field(default_factory=list, description="Allowed IP addresses")
    block_tor_exit_nodes: bool = Field(True, description="Block Tor exit nodes")

    # Request security
    max_request_size: int = Field(50 * 1024 * 1024, description="Max request size in bytes")
    request_timeout: int = Field(30, description="Request timeout in seconds")

    # Anti-abuse
    enable_rate_limiting: bool = Field(True, description="Enable rate limiting")
    enable_ddos_protection: bool = Field(True, description="Enable DDoS protection")


class RetryConfig(BaseModel):
    """Retry configuration"""

    max_attempts: int = Field(3, description="Maximum retry attempts")
    base_delay: float = Field(1.0, description="Base delay between retries")
    max_delay: float = Field(60.0, description="Maximum delay between retries")
    exponential_base: float = Field(2.0, description="Exponential backoff base")

    # Retry conditions
    retry_on_timeout: bool = Field(True, description="Retry on timeout")
    retry_on_connection_error: bool = Field(True, description="Retry on connection errors")
    retry_on_server_error: bool = Field(True, description="Retry on 5xx errors")
    retry_on_rate_limit: bool = Field(True, description="Retry on rate limiting")


class HealthCheckConfig(BaseModel):
    """Health check configuration"""

    enabled: bool = Field(True, description="Enable health checks")
    interval_seconds: int = Field(30, description="Health check interval")
    timeout_seconds: int = Field(10, description="Health check timeout")

    # Health check endpoints
    telegram_api_url: str = Field("https://api.telegram.org", description="Telegram API URL for health checks")
    custom_health_endpoint: Optional[str] = Field(None, description="Custom health check endpoint")


class APIConfig(BaseModel):
    """Main API configuration"""

    # Core settings
    bot_token: str = Field(..., description="Telegram bot token")
    environment: str = Field("development", description="Environment name")

    # API endpoints
    endpoints: APIEndpoints = Field(default_factory=APIEndpoints)

    # Rate limiting
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)

    # Security
    security: SecurityConfig = Field(default_factory=SecurityConfig)

    # Retry policy
    retry: RetryConfig = Field(default_factory=RetryConfig)

    # Health monitoring
    health_check: HealthCheckConfig = Field(default_factory=HealthCheckConfig)

    # Performance settings
    connection_pool_size: int = Field(10, description="HTTP connection pool size")
    max_connections: int = Field(100, description="Maximum concurrent connections")

    # Logging
    log_requests: bool = Field(False, description="Log API requests")
    log_responses: bool = Field(False, description="Log API responses")

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment setting"""
        if v not in ["development", "staging", "production"]:
            raise ValueError("Environment must be development, staging, or production")
        return v


@dataclass
class APIClient:
    """Enhanced Telegram Bot API client with advanced features"""

    config: APIConfig
    logger: Any = field(default_factory=lambda: structlog.get_logger())

    def __post_init__(self):
        """Initialize HTTP client and rate limiter"""
        self._client = None
        self._rate_limiter = None
        self._request_times = []
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize the API client"""
        # Initialize HTTP client with optimized settings
        limits = httpx.Limits(
            max_keepalive_connections=self.config.connection_pool_size,
            max_connections=self.config.max_connections
        )

        timeout = httpx.Timeout(
            connect=10.0,
            read=self.config.security.request_timeout,
            write=10.0,
            pool=5.0
        )

        self._client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            verify=self.config.security.validate_ssl_certificate
        )

        # Initialize rate limiter (simple token bucket)
        self._rate_limiter = {
            'tokens': self.config.rate_limit.requests_per_second,
            'last_update': time.time(),
            'rate': self.config.rate_limit.requests_per_second
        }

        self.logger.info(
            "API client initialized",
            environment=self.config.environment,
            rate_limit=self.config.rate_limit.requests_per_second
        )

    async def cleanup(self):
        """Cleanup resources"""
        if self._client:
            await self._client.aclose()
            self.logger.info("API client closed")

    def _check_rate_limit(self) -> bool:
        """Check if request is within rate limits"""
        if not self.config.security.enable_rate_limiting:
            return True

        now = time.time()

        # Simple token bucket implementation
        time_passed = now - self._rate_limiter['last_update']
        tokens_to_add = time_passed * self._rate_limiter['rate']

        self._rate_limiter['tokens'] = min(
            self._rate_limiter['rate'],
            self._rate_limiter['tokens'] + tokens_to_add
        )
        self._rate_limiter['last_update'] = now

        if self._rate_limiter['tokens'] >= 1.0:
            self._rate_limiter['tokens'] -= 1.0
            return True

        return False

    async def _wait_for_rate_limit(self):
        """Wait for rate limit to allow request"""
        if not self.config.security.enable_rate_limiting:
            return

        while not self._check_rate_limit():
            wait_time = 1.0 / self.config.rate_limit.requests_per_second
            await asyncio.sleep(wait_time)

    def _build_url(self, endpoint: str, **kwargs) -> str:
        """Build complete API URL"""
        url = self.config.endpoints.base_url + endpoint.format(token=self.config.bot_token, **kwargs)
        return url

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        retries_left: int = None,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry logic"""

        if retries_left is None:
            retries_left = self.config.retry.max_attempts

        # Wait for rate limit
        await self._wait_for_rate_limit()

        # Build URL
        url = self._build_url(endpoint, **kwargs)

        # Log request if enabled
        if self.config.log_requests:
            self.logger.debug("API request", method=method, url=url, kwargs=kwargs)

        try:
            # Make request
            response = await self._client.request(method, url, **kwargs)

            # Log response if enabled
            if self.config.log_responses:
                self.logger.debug(
                    "API response",
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )

            # Handle rate limiting
            if response.status_code == 429:
                if self.config.retry.retry_on_rate_limit and retries_left > 0:
                    retry_after = response.headers.get("Retry-After", 1)
                    wait_time = int(retry_after) + 1
                    self.logger.warning(f"Rate limited, retrying after {wait_time}s")
                    await asyncio.sleep(wait_time)
                    return await self._make_request(method, endpoint, retries_left - 1, **kwargs)
                else:
                    return response

            # Handle server errors
            if (response.status_code >= 500 and
                self.config.retry.retry_on_server_error and
                retries_left > 0):

                delay = self.config.retry.base_delay * (self.config.retry.exponential_base ** (self.config.retry.max_attempts - retries_left))
                delay = min(delay, self.config.retry.max_delay)

                self.logger.warning(f"Server error, retrying after {delay}s")
                await asyncio.sleep(delay)
                return await self._make_request(method, endpoint, retries_left - 1, **kwargs)

            return response

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if retries_left > 0:
                delay = self.config.retry.base_delay * (self.config.retry.exponential_base ** (self.config.retry.max_attempts - retries_left))
                delay = min(delay, self.config.retry.max_delay)

                self.logger.warning(f"Request failed, retrying after {delay}s: {e}")
                await asyncio.sleep(delay)
                return await self._make_request(method, endpoint, retries_left - 1, **kwargs)
            else:
                raise

    async def get_me(self) -> Dict[str, Any]:
        """Get bot information"""
        response = await self._make_request("GET", self.config.endpoints.get_me)
        response.raise_for_status()
        return response.json()

    async def send_message(
        self,
        chat_id: int,
        text: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Send text message"""
        data = {
            "chat_id": chat_id,
            "text": text,
            **kwargs
        }

        response = await self._make_request(
            "POST",
            self.config.endpoints.send_message,
            json=data
        )
        response.raise_for_status()
        return response.json()

    async def set_webhook(
        self,
        webhook_url: str,
        certificate_path: Optional[Path] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Set webhook URL"""

        data = {"url": webhook_url, **kwargs}
        files = None

        if certificate_path and certificate_path.exists():
            with open(certificate_path, "rb") as cert_file:
                files = {"certificate": cert_file.read()}

        response = await self._make_request(
            "POST",
            self.config.endpoints.set_webhook,
            data=data,
            files=files
        )
        response.raise_for_status()
        return response.json()

    async def delete_webhook(self) -> Dict[str, Any]:
        """Delete webhook"""
        response = await self._make_request(
            "GET",
            self.config.endpoints.delete_webhook
        )
        response.raise_for_status()
        return response.json()

    async def get_webhook_info(self) -> Dict[str, Any]:
        """Get webhook information"""
        response = await self._make_request(
            "GET",
            self.config.endpoints.get_webhook_info
        )
        response.raise_for_status()
        return response.json()

    async def download_file(self, file_path: str) -> bytes:
        """Download file from Telegram servers"""
        url = self._build_url(
            self.config.endpoints.download_file,
            file_path=file_path
        )

        response = await self._client.get(url)
        response.raise_for_status()
        return response.content

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        start_time = time.time()

        try:
            # Test Telegram API connectivity
            await self.get_me()

            response_time = time.time() - start_time

            return {
                "status": "healthy",
                "response_time": response_time,
                "timestamp": time.time(),
                "environment": self.config.environment
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time(),
                "environment": self.config.environment
            }


class APIConfigManager:
    """API configuration manager for different environments"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_dir = project_root / "config"
        self.config_dir.mkdir(exist_ok=True)

    def create_environment_config(self, environment: str) -> APIConfig:
        """Create API configuration for specific environment"""

        # Base configuration
        base_config = {
            "environment": environment,
            "bot_token": f"your_bot_token_for_{environment}",
        }

        # Environment-specific overrides
        if environment == "development":
            base_config.update({
                "security": {
                    "validate_ssl_certificate": False,
                    "enable_rate_limiting": False,
                    "log_requests": True,
                    "log_responses": True
                },
                "rate_limit": {
                    "requests_per_second": 10,
                    "requests_per_minute": 500,
                    "burst_limit": 20
                }
            })

        elif environment == "staging":
            base_config.update({
                "security": {
                    "validate_ssl_certificate": True,
                    "enable_rate_limiting": True,
                    "log_requests": True,
                    "log_responses": False
                },
                "rate_limit": {
                    "requests_per_second": 20,
                    "requests_per_minute": 800,
                    "burst_limit": 30
                }
            })

        elif environment == "production":
            base_config.update({
                "security": {
                    "validate_ssl_certificate": True,
                    "enable_rate_limiting": True,
                    "log_requests": False,
                    "log_responses": False,
                    "webhook_secret_token": secrets.token_urlsafe(32)
                },
                "rate_limit": {
                    "requests_per_second": 30,
                    "requests_per_minute": 1000,
                    "burst_limit": 50
                },
                "retry": {
                    "max_attempts": 5,
                    "base_delay": 2.0,
                    "max_delay": 120.0
                }
            })

        return APIConfig(**base_config)

    def generate_config_files(self) -> Dict[str, Path]:
        """Generate API configuration files for all environments"""

        created_files = {}

        for environment in ["development", "staging", "production"]:
            # Create API config
            config = self.create_environment_config(environment)

            # Save as JSON
            config_file = self.config_dir / f"api_config_{environment}.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config.dict(), f, indent=2, ensure_ascii=False)

            created_files[environment] = config_file
            print(f"✅ Created API config: {config_file}")

            # Create .env entries
            env_file = self.project_root / f".env.{environment}"
            self._update_env_file(env_file, config)

        return created_files

    def _update_env_file(self, env_file: Path, config: APIConfig):
        """Update environment file with API settings"""

        if not env_file.exists():
            return

        # Read existing content
        lines = []
        with open(env_file, "r") as f:
            lines = f.readlines()

        # Update or add API settings
        api_settings = {
            "BOT_TOKEN": config.bot_token,
            "API_REQUEST_TIMEOUT": str(self.config.security.request_timeout),
            "API_RATE_LIMIT_RPS": str(self.config.rate_limit.requests_per_second),
            "WEBHOOK_SECRET_TOKEN": config.security.webhook_secret_token or "",
        }

        # Process lines
        updated_lines = []
        for line in lines:
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=", 1)[0].strip()
                if key in api_settings and api_settings[key]:
                    updated_lines.append(f"{key}={api_settings[key]}\n")
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        # Add missing settings
        for key, value in api_settings.items():
            if value and not any(key in line for line in updated_lines):
                updated_lines.append(f"{key}={value}\n")

        # Write back
        with open(env_file, "w") as f:
            f.writelines(updated_lines)

        print(f"✅ Updated {env_file} with API settings")


def create_api_integration_example() -> str:
    """Create API integration example code"""

    example_code = '''#!/usr/bin/env python3
"""
Telegram Bot API Integration Example

This example demonstrates how to use the enhanced API client
with proper error handling, rate limiting, and retry logic.
"""

import asyncio
import json
from pathlib import Path

from config.api_config import APIConfig, APIClient
from utils.logger import setup_logging


async def main():
    """Example usage of the API client"""

    # Setup logging
    setup_logging()

    # Load configuration
    config_file = Path("config/api_config_production.json")
    if config_file.exists():
        with open(config_file, "r") as f:
            config_data = json.load(f)
        config = APIConfig(**config_data)
    else:
        # Create default config
        config = APIConfig(
            bot_token="YOUR_BOT_TOKEN",
            environment="development"
        )

    # Initialize API client
    client = APIClient(config)
    await client.initialize()

    try:
        # Example 1: Get bot information
        print("🤖 Getting bot information...")
        bot_info = await client.get_me()
        print(f"Bot: {bot_info['result']['name']} (@{bot_info['result']['username']})")

        # Example 2: Send a message (replace with actual chat_id)
        # chat_id = 123456789  # Replace with actual chat ID
        # message_response = await client.send_message(
        #     chat_id=chat_id,
        #     text="Hello from the enhanced API client! 🤖"
        # )
        # print(f"Message sent: {message_response['result']['message_id']}")

        # Example 3: Setup webhook (for production)
        if config.environment == "production":
            webhook_url = "https://your-domain.com/webhook"
            certificate_path = Path("ssl/certificate.crt")

            print(f"🔗 Setting up webhook: {webhook_url}")
            webhook_result = await client.set_webhook(
                webhook_url=webhook_url,
                certificate_path=certificate_path
            )
            print(f"Webhook setup: {webhook_result['result']}")

        # Example 4: Health check
        print("🏥 Performing health check...")
        health = await client.health_check()
        print(f"Health status: {health}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Cleanup
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
'''

    return example_code


def main():
    """Main function to generate API configuration"""

    print("🔧 Telegram Bot API Configuration Generator")
    print("=" * 50)

    project_root = Path(__file__).parent.parent
    config_manager = APIConfigManager(project_root)

    try:
        # Generate configuration files
        print("📄 Generating API configuration files...")
        config_files = config_manager.generate_config_files()

        print(f"\n✅ Generated {len(config_files)} configuration files:")
        for env, path in config_files.items():
            print(f"  • {env}: {path}")

        # Create example integration code
        example_code = create_api_integration_example()
        example_file = project_root / "examples" / "api_integration_example.py"
        example_file.parent.mkdir(exist_ok=True)

        with open(example_file, "w", encoding="utf-8") as f:
            f.write(example_code)

        print(f"✅ Created API integration example: {example_file}")

        print("\n📋 Next steps:")
        print("1. Edit configuration files with your bot tokens")
        print("2. Customize rate limiting and security settings")
        print("3. Review the integration example")
        print("4. Test API connectivity before deployment")

    except Exception as e:
        print(f"❌ Error generating API configuration: {e}")
        exit(1)


if __name__ == "__main__":
    main()