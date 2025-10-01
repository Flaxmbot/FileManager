"""
Common handlers for unhandled messages and errors
"""

from aiogram import Router
from aiogram.types import Message

from src.services.user_service import UserService
from src.utils.logger import get_logger

logger = get_logger(__name__)
common_router = Router()


@common_router.message()
async def handle_unknown_message(message: Message) -> None:
    """Handle unknown messages and commands"""
    try:
        # Get or create user for activity tracking
        user_service = UserService()
        user = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        # Log unknown command for debugging
        logger.info(f"Unknown message from user {message.from_user.id}: {message.text}")

        # Send help message
        help_text = (
            "❓ <b>Unknown Command</b>\n\n"
            "I didn't understand that command. Here are the available commands:\n\n"
            "<b>🔐 Authentication:</b>\n"
            "• /start - Initialize bot and get help\n"
            "• /auth <token> - Authenticate with your device\n\n"
            "<b>📱 Device Management:</b>\n"
            "• /info - Get device information\n\n"
            "<b>📁 File Operations:</b>\n"
            "• /list <path> - List files and directories\n"
            "• /download <path> - Download file from device\n"
            "• /upload <file> - Upload file to device\n"
            "• /delete <path> - Delete file or folder\n"
            "• /search <query> - Search files on device\n\n"
            "<b>📷 Media Operations:</b>\n"
            "• /screenshot - Capture device screenshot\n"
            "• /screenview - Stream device screen\n\n"
            "<b>💡 Tips:</b>\n"
            "• First use /auth <token> to connect your device\n"
            "• Use /start to see detailed help\n"
            "• All file paths should start with /sdcard/ or similar\n\n"
            "<b>Need help?</b> Use /start for a complete guide."
        )

        await message.reply(help_text, parse_mode="HTML")

        # Update user's last activity
        await user_service.update_last_activity(user.id)

    except Exception as e:
        logger.error(f"Error in unknown message handler: {e}")
        await message.reply(
            "❌ <b>Error:</b> An unexpected error occurred.",
            parse_mode="HTML"
        )


async def handle_error(error: Exception, message: Message) -> None:
    """Handle errors in message processing"""
    logger.error(f"Error processing message from {message.from_user.id}: {error}")

    try:
        await message.reply(
            "❌ <b>Error:</b> An error occurred while processing your request.\n"
            "Please try again or contact support if the issue persists.",
            parse_mode="HTML"
        )
    except Exception:
        # If we can't even send an error message, just log it
        logger.error("Failed to send error message to user")