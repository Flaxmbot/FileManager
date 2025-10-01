#!/usr/bin/env python3
"""
Webhook Setup Automation Script

This script automates the process of setting up webhooks for the Telegram bot
with proper SSL certificate validation and security configurations.

Features:
- SSL certificate generation and validation
- Webhook URL configuration
- Self-signed certificate support for development
- Production-ready Let's Encrypt integration
- Webhook testing and validation
- Security best practices implementation

Usage:
    python scripts/setup_webhook.py --environment production
    python scripts/setup_webhook.py --domain example.com --ssl letsencrypt
"""

import argparse
import asyncio
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


class SSLManager:
    """SSL certificate management"""

    def __init__(self, cert_dir: Path):
        self.cert_dir = cert_dir
        self.cert_dir.mkdir(exist_ok=True)

    def generate_self_signed_certificate(
        self,
        domain: str,
        validity_days: int = 365
    ) -> Tuple[Path, Path]:
        """Generate self-signed SSL certificate"""

        print(f"🔐 Generating self-signed certificate for {domain}...")

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create certificate subject
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, domain),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FileManager Bot"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Development"),
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
        ])

        # Create certificate
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(domain),
                x509.DNSName(f"*.{domain}"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())

        # Save certificate and key
        key_file = self.cert_dir / f"{domain}.key"
        cert_file = self.cert_dir / f"{domain}.crt"

        with open(key_file, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"✅ Generated self-signed certificate: {cert_file}")
        print(f"✅ Generated private key: {key_file}")

        return cert_file, key_file

    def setup_letsencrypt(self, domain: str, email: str) -> Tuple[Path, Path]:
        """Setup Let's Encrypt SSL certificate"""

        print(f"🔐 Setting up Let's Encrypt for {domain}...")

        # Check if certbot is installed
        try:
            subprocess.run(["certbot", "--version"],
                         check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Certbot not found. Installing...")
            self._install_certbot()

        # Generate certificate
        cert_dir = Path("/etc/letsencrypt/live") / domain

        if not cert_dir.exists():
            print(f"Generating Let's Encrypt certificate for {domain}...")

            cmd = [
                "certbot", "certonly",
                "--standalone",
                "--agree-tos",
                "--no-eff-email",
                "--register-unsafely-without-email",
                "--email", email,
                "-d", domain,
                "--non-interactive"
            ]

            try:
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                print("✅ Let's Encrypt certificate generated successfully")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to generate Let's Encrypt certificate: {e}")
                print("Falling back to self-signed certificate...")
                return self.generate_self_signed_certificate(domain)

        cert_file = cert_dir / "cert.pem"
        key_file = cert_dir / "privkey.pem"

        if cert_file.exists() and key_file.exists():
            print(f"✅ Using existing Let's Encrypt certificate: {cert_file}")
            return cert_file, key_file
        else:
            print("❌ Let's Encrypt certificate files not found")
            return self.generate_self_signed_certificate(domain)

    def _install_certbot(self):
        """Install certbot"""
        try:
            if sys.platform == "linux":
                # Try snap first (Ubuntu/Debian)
                subprocess.run(["snap", "install", "core"], check=True)
                subprocess.run(["snap", "install", "--classic", "certbot"], check=True)
            else:
                print("❌ Automatic certbot installation not supported on this platform")
                print("Please install certbot manually and try again")
                sys.exit(1)
        except subprocess.CalledProcessError:
            print("❌ Failed to install certbot via snap")
            print("Please install certbot manually and try again")
            sys.exit(1)

    def validate_certificate(self, cert_path: Path) -> bool:
        """Validate SSL certificate"""
        try:
            with open(cert_path, "rb") as f:
                cert_data = f.read()

            cert = x509.load_pem_x509_certificate(cert_data)

            # Check if certificate is not expired
            if cert.not_valid_after < datetime.utcnow():
                print(f"❌ Certificate expired on {cert.not_valid_after}")
                return False

            # Check if certificate is valid now
            if cert.not_valid_before > datetime.utcnow():
                print(f"❌ Certificate not yet valid (valid from {cert.not_valid_before})")
                return False

            print(f"✅ Certificate is valid until {cert.not_valid_after}")
            return True

        except Exception as e:
            print(f"❌ Certificate validation failed: {e}")
            return False


class WebhookManager:
    """Telegram webhook management"""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def test_bot_token(self) -> bool:
        """Test if bot token is valid"""
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=10)
            if response.status_code == 200:
                bot_info = response.json()
                if bot_info.get("ok"):
                    bot_data = bot_info["result"]
                    print(f"✅ Bot token valid: {bot_data['name']} (@{bot_data['username']})")
                    return True
            print(f"❌ Invalid bot token: {response.text}")
            return False
        except Exception as e:
            print(f"❌ Failed to validate bot token: {e}")
            return False

    def set_webhook(
        self,
        webhook_url: str,
        certificate_path: Optional[Path] = None,
        max_connections: int = 40,
        drop_pending_updates: bool = True
    ) -> bool:
        """Set bot webhook"""

        data = {
            "url": webhook_url,
            "max_connections": max_connections,
            "drop_pending_updates": drop_pending_updates
        }

        files = None
        if certificate_path and certificate_path.exists():
            files = {"certificate": certificate_path.read_bytes()}

        try:
            if files:
                response = requests.post(f"{self.base_url}/setWebhook", data=data, files=files, timeout=30)
            else:
                response = requests.post(f"{self.base_url}/setWebhook", data=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    print(f"✅ Webhook set successfully: {webhook_url}")
                    return True
                else:
                    print(f"❌ Failed to set webhook: {result.get('description', 'Unknown error')}")
            else:
                print(f"❌ HTTP error setting webhook: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"❌ Error setting webhook: {e}")

        return False

    def get_webhook_info(self) -> Optional[Dict]:
        """Get current webhook information"""
        try:
            response = requests.get(f"{self.base_url}/getWebhookInfo", timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return result["result"]
        except Exception as e:
            print(f"❌ Error getting webhook info: {e}")
        return None

    def delete_webhook(self) -> bool:
        """Delete current webhook"""
        try:
            response = requests.get(f"{self.base_url}/deleteWebhook", timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    print("✅ Webhook deleted successfully")
                    return True
            print(f"❌ Failed to delete webhook: {response.text}")
        except Exception as e:
            print(f"❌ Error deleting webhook: {e}")
        return False

    def test_webhook(self, webhook_url: str) -> bool:
        """Test webhook endpoint"""
        try:
            # Send test request to webhook
            test_data = {
                "test": True,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Webhook test from setup script"
            }

            response = requests.post(
                webhook_url,
                json=test_data,
                timeout=10,
                headers={"User-Agent": "TelegramBot-Setup/1.0"}
            )

            if response.status_code in [200, 201, 202]:
                print(f"✅ Webhook endpoint is responding (HTTP {response.status_code})")
                return True
            else:
                print(f"⚠️ Webhook endpoint returned HTTP {response.status_code}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot reach webhook endpoint: {e}")
            return False


class WebhookSetupAutomation:
    """Main webhook setup automation class"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.ssl_dir = self.project_root / "ssl"
        self.config_dir = self.project_root / "config"

        # Create directories
        self.ssl_dir.mkdir(exist_ok=True)

        # Initialize managers
        self.ssl_manager = SSLManager(self.ssl_dir)

    def load_environment_config(self, environment: str) -> Dict:
        """Load environment configuration"""
        env_file = self.project_root / f".env.{environment}"
        if not env_file.exists():
            print(f"❌ Environment file not found: {env_file}")
            return {}

        config = {}
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()

        return config

    def setup_webhook_for_environment(self, environment: str, domain: str = None, ssl_type: str = "auto") -> bool:
        """Setup webhook for specific environment"""

        print(f"🚀 Setting up webhook for {environment} environment")
        print("=" * 60)

        # Load environment configuration
        config = self.load_environment_config(environment)
        if not config:
            return False

        bot_token = config.get("BOT_TOKEN")
        if not bot_token or bot_token == "your_bot_token_here":
            print("❌ BOT_TOKEN not configured in environment file")
            print(f"Please edit .env.{environment} and set your bot token")
            return False

        # Initialize webhook manager
        webhook_manager = WebhookManager(bot_token)

        # Test bot token
        if not webhook_manager.test_bot_token():
            return False

        # Determine domain
        if not domain:
            if environment == "production":
                domain = input("Enter your production domain (e.g., api.example.com): ").strip()
            else:
                domain = f"{environment}.localhost"

        # Setup SSL certificate
        cert_file = None
        key_file = None

        if ssl_type == "letsencrypt":
            email = input("Enter email for Let's Encrypt: ").strip()
            cert_file, key_file = self.ssl_manager.setup_letsencrypt(domain, email)
        elif ssl_type == "selfsigned":
            cert_file, key_file = self.ssl_manager.generate_self_signed_certificate(domain)
        else:  # auto
            if environment == "production":
                print("🔄 Production environment detected, trying Let's Encrypt...")
                email = input("Enter email for Let's Encrypt: ").strip()
                cert_file, key_file = self.ssl_manager.setup_letsencrypt(domain, email)
            else:
                print("🔄 Development/Staging environment detected, using self-signed...")
                cert_file, key_file = self.ssl_manager.generate_self_signed_certificate(domain)

        # Validate certificate
        if cert_file and not self.ssl_manager.validate_certificate(cert_file):
            print("❌ Certificate validation failed")
            return False

        # Construct webhook URL
        webhook_url = f"https://{domain}/webhook"

        # Test webhook endpoint (if server is running)
        print("🔍 Testing webhook endpoint...")
        endpoint_ok = webhook_manager.test_webhook(webhook_url)

        if not endpoint_ok:
            print("⚠️ Webhook endpoint not accessible")
            if not self.confirm_action("Continue anyway? (webhook will be set but may not work)"):
                return False

        # Set webhook
        print("📡 Setting webhook...")
        success = webhook_manager.set_webhook(
            webhook_url=webhook_url,
            certificate_path=cert_file,
            max_connections=40 if environment == "production" else 10,
            drop_pending_updates=True
        )

        if success:
            # Update environment file
            self.update_environment_config(environment, {
                "BOT_WEBHOOK_URL": webhook_url,
                "SSL_CERT_PATH": str(cert_file) if cert_file else "",
                "SSL_KEY_PATH": str(key_file) if key_file else "",
                "WEBHOOK_CONFIGURED": "true"
            })

            print("
✅ Webhook setup completed successfully!"            print(f"🌐 Webhook URL: {webhook_url}")
            print(f"🔐 SSL Certificate: {cert_file}")
            print(f"🔑 SSL Private Key: {key_file}")

            if environment == "production":
                print("
📋 Next steps for production:"                print("1. Ensure your domain points to this server")
                print("2. Configure your firewall to allow HTTPS (port 443)")
                print("3. Set up SSL certificate auto-renewal")
                print("4. Monitor webhook delivery in Telegram")

            return True

        return False

    def update_environment_config(self, environment: str, updates: Dict[str, str]):
        """Update environment configuration file"""
        env_file = self.project_root / f".env.{environment}"

        if not env_file.exists():
            print(f"❌ Environment file not found: {env_file}")
            return

        # Read current content
        lines = []
        with open(env_file, "r") as f:
            lines = f.readlines()

        # Update existing values or add new ones
        updated_keys = set()
        for i, line in enumerate(lines):
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=", 1)[0].strip()
                if key in updates:
                    lines[i] = f"{key}={updates[key]}\n"
                    updated_keys.add(key)

        # Add missing keys
        for key, value in updates.items():
            if key not in updated_keys:
                lines.append(f"{key}={value}\n")

        # Write back
        with open(env_file, "w") as f:
            f.writelines(lines)

        print(f"✅ Updated {env_file}")

    def confirm_action(self, message: str) -> bool:
        """Get user confirmation"""
        response = input(f"{message} (y/N): ").strip().lower()
        return response in ['y', 'yes']

    def run_interactive_setup(self):
        """Run interactive webhook setup"""
        print("🤖 Telegram Bot Webhook Setup Automation")
        print("=" * 60)
        print()
        print("This script will help you set up webhooks for your Telegram bot.")
        print("Make sure your bot is already created via BotFather.")
        print()

        # Environment selection
        print("Select environment:")
        print("1. Development (localhost)")
        print("2. Staging (staging server)")
        print("3. Production (live server)")

        while True:
            choice = input("Enter choice (1-3): ").strip()
            if choice == "1":
                environment = "development"
                break
            elif choice == "2":
                environment = "staging"
                break
            elif choice == "3":
                environment = "production"
                break
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")

        # Domain configuration
        domain = None
        if environment == "production":
            domain = input("Enter your production domain (e.g., api.example.com): ").strip()
        else:
            domain = input(f"Enter domain for {environment} (default: {environment}.localhost): ").strip()
            if not domain:
                domain = f"{environment}.localhost"

        # SSL configuration
        print("
SSL Certificate options:"        print("1. Let's Encrypt (recommended for production)")
        print("2. Self-signed (for development/testing)")

        ssl_choice = input("Enter choice (1-2): ").strip()
        ssl_type = "letsencrypt" if ssl_choice == "1" else "selfsigned"

        # Run setup
        success = self.setup_webhook_for_environment(environment, domain, ssl_type)

        if success:
            print("
🎉 Webhook setup completed!"            print("Your bot is now configured to receive webhooks.")
        else:
            print("
❌ Webhook setup failed."            print("Please check the errors above and try again.")

    def run_command_line_setup(self, args):
        """Run command line webhook setup"""
        environment = args.environment
        domain = args.domain
        ssl_type = args.ssl

        success = self.setup_webhook_for_environment(environment, domain, ssl_type)

        if not success:
            sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Telegram Bot Webhook Setup Automation")
    parser.add_argument(
        "--environment", "-e",
        choices=["development", "staging", "production"],
        help="Environment to configure"
    )
    parser.add_argument(
        "--domain", "-d",
        help="Domain name for webhook"
    )
    parser.add_argument(
        "--ssl",
        choices=["letsencrypt", "selfsigned", "auto"],
        default="auto",
        help="SSL certificate type"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run interactive setup"
    )

    args = parser.parse_args()

    setup = WebhookSetupAutomation()

    if args.interactive or not args.environment:
        setup.run_interactive_setup()
    else:
        setup.run_command_line_setup(args)


if __name__ == "__main__":
    main()