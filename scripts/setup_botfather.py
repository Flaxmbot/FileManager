#!/usr/bin/env python3
"""
BotFather Setup Automation Script

This script provides interactive guidance for setting up a Telegram bot using BotFather.
It walks users through the entire process and generates configuration files.

Usage:
    python scripts/setup_botfather.py
"""

import asyncio
import json
import os
import secrets
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional

import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class BotFatherSetup:
    """Interactive BotFather setup automation"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.config_dir = self.project_root / "config"
        self.scripts_dir = self.project_root / "scripts"
        self.keys_dir = self.project_root / "keys"

        # Create necessary directories
        self.config_dir.mkdir(exist_ok=True)
        self.keys_dir.mkdir(exist_ok=True)

        # BotFather commands
        self.botfather_commands = {
            'newbot': '/newbot',
            'setname': '/setname',
            'setdescription': '/setdescription',
            'setabout': '/setabout',
            'setcommands': '/setcommands',
            'setmenubutton': '/setmenubutton',
            'setdomain': '/setdomain',
            'deletebot': '/deletebot'
        }

    def print_header(self):
        """Print setup header"""
        print("=" * 60)
        print("🤖 Telegram BotFather Setup Automation")
        print("=" * 60)
        print()
        print("This script will guide you through setting up your Telegram bot.")
        print("Make sure you have Telegram installed and are logged in.")
        print()

    def print_step(self, step: int, total: int, description: str):
        """Print current step"""
        print(f"📋 Step {step}/{total}: {description}")
        print("-" * 50)

    def get_user_input(self, prompt: str, required: bool = True, default: str = None) -> str:
        """Get user input with validation"""
        while True:
            value = input(f"{prompt}: ").strip()
            if not value:
                if default:
                    return default
                elif not required:
                    return ""
                else:
                    print("❌ This field is required.")
                    continue
            return value

    def confirm_action(self, message: str) -> bool:
        """Get user confirmation"""
        response = input(f"{message} (y/N): ").strip().lower()
        return response in ['y', 'yes']

    def generate_secure_keys(self) -> Dict[str, str]:
        """Generate secure encryption keys"""
        print("🔐 Generating secure encryption keys...")

        # Generate Fernet key for symmetric encryption
        fernet_key = Fernet.generate_key().decode()

        # Generate RSA key pair for asymmetric encryption
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )

        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()

        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()

        # Save keys to files
        with open(self.keys_dir / "private.pem", "w") as f:
            f.write(private_pem)
        with open(self.keys_dir / "public.pem", "w") as f:
            f.write(public_pem)

        print(f"✅ Keys generated and saved to {self.keys_dir}")

        return {
            'fernet_key': fernet_key,
            'private_key': private_pem,
            'public_key': public_pem
        }

    def create_bot_commands_config(self) -> str:
        """Create bot commands configuration"""
        commands = """start - Start the bot and get help
auth - Authenticate your device (get token from Android app)
list - List files in a directory (/list /sdcard/Documents)
download - Download a file (/download /path/to/file)
upload - Upload a file (reply to file with /upload)
delete - Delete a file or folder (/delete /path/to/file)
search - Search for files (/search query)
screenshot - Take a screenshot
screenview - View device screen (streaming)
info - Get device information
help - Show detailed help"""

        commands_file = self.config_dir / "bot_commands.txt"
        with open(commands_file, "w") as f:
            f.write(commands)

        return commands_file

    def open_telegram_botfather(self) -> bool:
        """Open BotFather in Telegram"""
        print("\n🔗 Opening BotFather in Telegram...")
        print("Please follow these steps:")
        print("1. Search for @BotFather in Telegram")
        print("2. Start a conversation with @BotFather")
        print("3. Send the commands as shown below")
        print()

        if self.confirm_action("Have you opened BotFather in Telegram?"):
            return True

        print("📱 Opening Telegram application...")
        try:
            if sys.platform == "win32":
                os.startfile("https://t.me/botfather")
            elif sys.platform == "darwin":  # macOS
                subprocess.run(["open", "https://t.me/botfather"])
            else:  # Linux
                subprocess.run(["xdg-open", "https://t.me/botfather"])

            input("Press Enter after opening BotFather in Telegram...")
            return True
        except Exception as e:
            print(f"❌ Could not open Telegram: {e}")
            print("Please manually open: https://t.me/botfather")
            return self.confirm_action("Have you opened BotFather?")

    def guide_bot_creation(self) -> Dict[str, str]:
        """Guide user through bot creation process"""
        print("\n🤖 Bot Creation Process")
        print("=" * 30)

        print("Step 1: Create a new bot")
        print("Send this command to BotFather:")
        print("/newbot")

        bot_name = self.get_user_input("Enter your bot's display name (e.g., 'FileManager Bot')")
        bot_username = self.get_user_input("Enter your bot's username (must end with 'bot', e.g., 'mymanagerbot')")

        print(f"\n📝 Send these details to BotFather:")
        print(f"Display Name: {bot_name}")
        print(f"Username: @{bot_username}")
        print()

        input("Press Enter after completing bot creation and receiving the token...")

        bot_token = self.get_user_input("Enter the bot token from BotFather")

        print("\n✅ Bot created successfully!")
        return {
            'name': bot_name,
            'username': bot_username,
            'token': bot_token
        }

    def guide_bot_configuration(self, bot_info: Dict[str, str]) -> Dict[str, str]:
        """Guide user through bot configuration"""
        print("\n⚙️ Bot Configuration")
        print("=" * 20)

        config_options = {
            'name': {
                'command': '/setname',
                'description': "Set bot's display name",
                'current': bot_info['name']
            },
            'description': {
                'command': '/setdescription',
                'description': "Set bot description",
                'current': "Remote Android device control and file management bot"
            },
            'about': {
                'command': '/setabout',
                'description': "Set about text",
                'current': "🤖 Secure file management and device control bot with RSA-4096 encryption"
            }
        }

        for key, option in config_options.items():
            print(f"\n{option['description']}:")
            print(f"Current: {option['current']}")
            print(f"Command: {option['command']}")

            if self.confirm_action(f"Configure {key}?"):
                print(f"Send this to BotFather: {option['command']}")
                input(f"Press Enter after setting the {key}...")

        # Set bot commands
        print("📋 Setting bot commands..."   
                  commands_file = self.create_bot_commands_config()
        print(f"Commands file created: {commands_file}")
        print("Send this command to BotFather: /setcommands")
        print("Then upload the commands file when prompted")
        input("Press Enter after setting commands...")

        return config_options

    def create_environment_configs(self, bot_info: Dict[str, str], keys: Dict[str, str]) -> Dict[str, str]:
        """Create environment-specific configuration files"""
        print("\n📄 Creating configuration files...")

        base_config = {
            'BOT_TOKEN': bot_info['token'],
            'SECRET_KEY': secrets.token_urlsafe(32),
            'ENCRYPTION_KEY': keys['fernet_key'],
            'RSA_PRIVATE_KEY_PATH': 'keys/private.pem',
            'RSA_PUBLIC_KEY_PATH': 'keys/public.pem',
        }

        # Development config
        dev_config = {
            **base_config,
            'ENVIRONMENT': 'development',
            'DATABASE_URL': 'postgresql+asyncpg://filemanager_dev:dev_password@localhost:5432/filemanager_dev',
            'REDIS_URL': 'redis://localhost:6379/0',
            'LOG_LEVEL': 'DEBUG',
            'API_HOST': 'localhost',
            'API_PORT': '8000',
        }

        # Staging config
        staging_config = {
            **base_config,
            'ENVIRONMENT': 'staging',
            'DATABASE_URL': 'postgresql+asyncpg://filemanager_staging:staging_password@localhost:5432/filemanager_staging',
            'REDIS_URL': 'redis://localhost:6379/1',
            'LOG_LEVEL': 'INFO',
            'API_HOST': '0.0.0.0',
            'API_PORT': '8000',
        }

        # Production config
        prod_config = {
            **base_config,
            'ENVIRONMENT': 'production',
            'DATABASE_URL': 'postgresql+asyncpg://filemanager_prod:prod_password@localhost:5432/filemanager_prod',
            'REDIS_URL': 'redis://localhost:6379/2',
            'LOG_LEVEL': 'WARNING',
            'API_HOST': '0.0.0.0',
            'API_PORT': '8000',
        }

        # Write configuration files
        configs = {
            'development': dev_config,
            'staging': staging_config,
            'production': prod_config
        }

        for env, config in configs.items():
            env_file = self.project_root / f".env.{env}"
            with open(env_file, "w") as f:
                for key, value in config.items():
                    f.write(f"{key}={value}\n")
            print(f"✅ Created {env_file}")

        # Create main .env file (defaults to development)
        with open(self.project_root / ".env", "w") as f:
            for key, value in dev_config.items():
                f.write(f"{key}={value}\n")
        print("✅ Created .env (development)"

        return {env: config for env, config in configs.items()}

    def create_setup_summary(self, bot_info: Dict[str, str], configs: Dict[str, str]) -> str:
        """Create setup summary file"""
        summary = f"""# Telegram Bot Setup Summary
Generated on: {__import__('datetime').datetime.now().isoformat()}

## Bot Information
- Name: {bot_info['name']}
- Username: @{bot_info['username']}
- Token: {bot_info['token'][:20]}...

## Configuration Files Created
- .env (development)
- .env.staging
- .env.production

## Next Steps
1. Set up PostgreSQL database for your environment
2. Run database migrations: python -m alembic upgrade head
3. Start the bot: python -m src.main
4. Test bot functionality with /start command

## Security Notes
- RSA-4096 keys generated and stored in keys/ directory
- Keep your bot token secure and never commit it to version control
- Use different database credentials for each environment
- Enable webhook for production deployment

## Support
For issues or questions, refer to the troubleshooting guide or create an issue in the repository.
"""

        summary_file = self.project_root / "SETUP_SUMMARY.md"
        with open(summary_file, "w") as f:
            f.write(summary)

        print(f"✅ Created setup summary: {summary_file}")
        return summary_file

    def run_setup(self):
        """Run the complete setup process"""
        self.print_header()

        try:
            # Step 1: Generate keys
            self.print_step(1, 6, "Generate secure encryption keys")
            keys = self.generate_secure_keys()

            # Step 2: Open BotFather
            self.print_step(2, 6, "Open BotFather in Telegram")
            if not self.open_telegram_botfather():
                print("❌ Cannot proceed without BotFather access")
                return

            # Step 3: Create bot
            self.print_step(3, 6, "Create new bot")
            bot_info = self.guide_bot_creation()

            # Step 4: Configure bot
            self.print_step(4, 6, "Configure bot settings")
            config_info = self.guide_bot_configuration(bot_info)

            # Step 5: Create environment configs
            self.print_step(5, 6, "Create environment configuration files")
            configs = self.create_environment_configs(bot_info, keys)

            # Step 6: Create summary
            self.print_step(6, 6, "Create setup summary")
            summary_file = self.create_setup_summary(bot_info, configs)

            print("\n🎉 Setup completed successfully!")
            print("=" * 60)
            print("Your bot is ready to use!")
            print(f"📄 Check {summary_file} for next steps")
            print("🚀 Run 'python -m src.main' to start your bot")

        except KeyboardInterrupt:
            print("\n\n⚠️ Setup interrupted by user")
        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            print("Check the error and try again")


def main():
    """Main entry point"""
    setup = BotFatherSetup()
    setup.run_setup()


if __name__ == "__main__":
    main()