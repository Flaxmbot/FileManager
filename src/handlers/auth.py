"""
Authentication command handler
"""

from aiogram import Router
from aiogram.types import Message

from src.services.device_service import DeviceService
from src.services.user_service import UserService
from src.utils.logger import get_logger

logger = get_logger(__name__)
auth_router = Router()


@auth_router.message(commands=["auth"])
async def cmd_auth(message: Message) -> None:
    """Handle /auth command for device authentication"""
    try:
        # Parse authentication token
        args = message.text.split()
        if len(args) < 2:
            await message.reply(
                "❌ <b>Usage:</b> /auth <token>\n\n"
                "<b>Example:</b> /auth abc123def456\n\n"
                "Get your authentication token from the FileManager Android app:\n"
                "Settings > Telegram Bot > Generate Token",
                parse_mode="HTML"
            )
            return

        auth_token = args[1].strip()

        if len(auth_token) < 10:
            await message.reply(
                "❌ <b>Invalid Token:</b> Authentication token appears to be too short.\n"
                "Please ensure you're using the correct token from your Android app.",
                parse_mode="HTML"
            )
            return

        # Get user
        user_service = UserService()
        user = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        # Process authentication
        device_service = DeviceService()
        device = await device_service.authenticate_device(user.id, auth_token)

        if not device:
            await message.reply(
                "❌ <b>Authentication Failed:</b>\n\n"
                "Possible reasons:\n"
                "• Invalid or expired token\n"
                "• Token already used\n"
                "• Device not properly configured\n\n"
                "Please generate a new token in your Android app and try again.",
                parse_mode="HTML"
            )
            return

        # Success message
        await message.reply(
            "✅ <b>Authentication Successful!</b>\n\n"
            f"📱 <b>Device:</b> {device.device_name}\n"
            f"🔗 <b>Device ID:</b> <code>{device.device_id}</code>\n"
            f"📊 <b>Status:</b> {device.status.value.title()}\n\n"
            "You can now use all bot commands:\n"
            "• /list - Browse files\n"
            "• /download - Download files\n"
            "• /upload - Upload files\n"
            "• /screenshot - Capture screen\n"
            "• /screenview - View screen\n"
            "• /info - Device information\n"
            "• /search - Search files",
            parse_mode="HTML"
        )

        # Update user's last activity
        await user_service.update_last_activity(user.id)

        logger.info(f"User {user.id} authenticated device {device.device_id}")

    except Exception as e:
        logger.error(f"Error in auth command: {e}")
        await message.reply(
            "❌ <b>Error:</b> An unexpected error occurred during authentication.\n"
            "Please try again or contact support if the issue persists.",
            parse_mode="HTML"
        )