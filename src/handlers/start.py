"""
Start command handler
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from src.services.user_service import UserService

start_router = Router()


@start_router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Handle /start command"""
    try:
        # Debug logging
        print(f"Received /start from user {message.from_user.id}")

        user_service = UserService()

        # Get or create user
        user = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code
        )

        # Welcome message with interactive buttons
        welcome_text = (
            "🤖 <b>Welcome to FileManager Bot!</b>\n\n"
            "📱 <b>Remote Android Device Control</b>\n\n"
            "This bot lets you:\n"
            "📁 Browse and manage files\n"
            "📷 Take screenshots\n"
            "📺 View device screen\n"
            "🔒 Secure encrypted connection\n\n"
            "<b>🚀 Quick Start:</b>\n"
            "1️⃣ Install FileManager Android app\n"
            "2️⃣ Generate auth token in app\n"
            "3️⃣ Send /auth [your_token]\n"
            "4️⃣ Start exploring your files!\n\n"
            "Use the buttons below to get started! 👇"
        )

        # Create inline keyboard for better UX
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Connect Device", callback_data="connect_device")],
            [InlineKeyboardButton(text="📋 Commands Help", callback_data="show_commands")],
            [InlineKeyboardButton(text="ℹ️ About", callback_data="about_bot")]
        ])

        await message.reply(
            welcome_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

        await message.reply(
            welcome_text,
            parse_mode="HTML"
        )

        # Update user's last activity
        await user_service.update_last_activity(user.id)

        print(f"Successfully responded to /start from user {message.from_user.id}")

    except Exception as e:
        print(f"Error in /start handler: {e}")
        import traceback
        traceback.print_exc()
        # Send error message to user
        await message.reply(
            "❌ <b>Error:</b> An error occurred while processing your request.\n"
            "Please try again later.",
            parse_mode="HTML"
        )


@start_router.callback_query(lambda c: c.data == "connect_device")
async def handle_connect_device(callback: CallbackQuery):
    """Handle connect device button"""
    await callback.message.edit_text(
        "🔗 <b>Connect Your Device</b>\n\n"
        "To connect your Android device:\n\n"
        "1️⃣ <b>Install FileManager App</b>\n"
        "Download and install the FileManager Android app\n\n"
        "2️⃣ <b>Generate Auth Token</b>\n"
        "Open the app → Settings → Telegram Bot → Generate Token\n\n"
        "3️⃣ <b>Send Token</b>\n"
        "Send: <code>/auth [your_token_here]</code>\n\n"
        "Example: <code>/auth abc123def456</code>\n\n"
        "✅ Your device will be connected and ready to use!",
        parse_mode="HTML",
        reply_markup=None
    )
    await callback.answer()


@start_router.callback_query(lambda c: c.data == "show_commands")
async def handle_show_commands(callback: CallbackQuery):
    """Handle show commands button"""
    await callback.message.edit_text(
        "📋 <b>Available Commands</b>\n\n"
        "📁 <b>File Operations:</b>\n"
        "• /list [path] - Browse files\n"
        "• /download [file] - Download file\n"
        "• /upload [file] - Upload file\n"
        "• /delete [file] - Delete file\n"
        "• /search [query] - Search files\n\n"
        "📱 <b>Device Control:</b>\n"
        "• /info - Device information\n"
        "• /screenshot - Take screenshot\n"
        "• /screenview - View screen\n\n"
        "🔐 <b>Authentication:</b>\n"
        "• /auth [token] - Connect device\n\n"
        "<i>💡 Tip: Use /list /sdcard/ to start browsing!</i>",
        parse_mode="HTML",
        reply_markup=None
    )
    await callback.answer()


@start_router.callback_query(lambda c: c.data == "about_bot")
async def handle_about_bot(callback: CallbackQuery):
    """Handle about bot button"""
    await callback.message.edit_text(
        "ℹ️ <b>About FileManager Bot</b>\n\n"
        "🤖 <b>Features:</b>\n"
        "• Remote file management\n"
        "• Screenshot capture\n"
        "• Screen streaming\n"
        "• Secure encrypted connection\n"
        "• Real-time file browsing\n\n"
        "🔒 <b>Security:</b>\n"
        "• End-to-end encryption\n"
        "• Token-based authentication\n"
        "• Secure WebSocket connection\n\n"
        "📱 <b>Requirements:</b>\n"
        "• Android device with FileManager app\n"
        "• Active internet connection\n"
        "• Telegram account\n\n"
        "🚀 Ready to explore your files!",
        parse_mode="HTML",
        reply_markup=None
    )
    await callback.answer()