"""
Start command handler
"""

from aiogram import Router
from aiogram.types import Message

from src.services.user_service import UserService

start_router = Router()


@start_router.message(commands=["start"])
async def cmd_start(message: Message) -> None:
    """Handle /start command"""
    user_service = UserService()

    # Get or create user
    user = await user_service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code
    )

    # Welcome message
    welcome_text = (
        "🤖 <b>Welcome to FileManager Bot!</b>\n\n"
        "This bot allows you to remotely control your Android device and manage files.\n\n"
        "<b>Available Commands:</b>\n"
        "📱 <b>Device Management:</b>\n"
        "• /auth <token> - Authenticate with your device\n"
        "• /info - Get device information\n\n"
        "📁 <b>File Operations:</b>\n"
        "• /list <path> - List files and directories\n"
        "• /download <path> - Download file from device\n"
        "• /upload <file> - Upload file to device\n"
        "• /delete <path> - Delete file or folder\n"
        "• /search <query> - Search files on device\n\n"
        "📷 <b>Media Operations:</b>\n"
        "• /screenshot - Capture device screenshot\n"
        "• /screenview - Stream device screen\n\n"
        "<b>Getting Started:</b>\n"
        "1. Install the FileManager Android app\n"
        "2. Generate an authentication token in the app\n"
        "3. Use /auth <token> to connect your device\n"
        "4. Start managing your files remotely!\n\n"
        "🔒 All communication is encrypted and secure."
    )

    await message.reply(
        welcome_text,
        parse_mode="HTML"
    )

    # Update user's last activity
    await user_service.update_last_activity(user.id)