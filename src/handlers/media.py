"""
Media operations command handlers (screenshot, screenview)
"""

import asyncio
import os
from typing import Optional

from aiogram import Router
from aiogram.types import Message

from src.services.device_manager import DeviceManager
from src.services.user_service import UserService
from src.utils.logger import get_logger

logger = get_logger(__name__)
media_router = Router()


@media_router.message(commands=["screenshot"])
async def cmd_screenshot(message: Message) -> None:
    """Handle /screenshot command to capture device screenshot"""
    try:
        # Get user and check permissions
        user_service = UserService()
        user = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        if not user.has_permission("screenshot"):
            await message.reply(
                "❌ <b>Access Denied:</b> You don't have permission to capture screenshots.",
                parse_mode="HTML"
            )
            return

        # Get device and check connection
        user_devices = await user_service.get_user_devices(user.id)
        if not user_devices:
            await message.reply(
                "❌ <b>No Devices:</b> No devices found for your account.\n"
                "Use /auth <token> to connect a device first.",
                parse_mode="HTML"
            )
            return

        device = user_devices[0]
        device_manager = DeviceManager()

        if not await device_manager.is_device_connected(device.device_id):
            await message.reply(
                "❌ <b>Device Offline:</b> Your device is not connected.\n"
                "Please ensure your Android app is running and connected.",
                parse_mode="HTML"
            )
            return

        # Request screenshot
        await message.reply("📸 <b>Capturing screenshot...</b>", parse_mode="HTML")

        screenshot_data = await device_manager.request_screenshot(device.device_id)

        if not screenshot_data:
            await message.reply(
                "❌ <b>Screenshot Failed:</b> Could not capture screenshot.\n"
                "Please ensure your device screen is accessible.",
                parse_mode="HTML"
            )
            return

        # Save screenshot temporarily
        temp_filename = f"screenshot_{device.device_id[:8]}_{message.from_user.id}.png"
        with open(temp_filename, "wb") as f:
            f.write(screenshot_data)

        try:
            # Send screenshot to user
            await message.reply_photo(
                open(temp_filename, "rb"),
                caption=f"📸 Screenshot from {device.device_name}"
            )
        finally:
            # Clean up temporary file
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

        # Update user's last activity
        await user_service.update_last_activity(user.id)

    except Exception as e:
        logger.error(f"Error in screenshot command: {e}")
        await message.reply(
            "❌ <b>Error:</b> An unexpected error occurred while capturing screenshot.",
            parse_mode="HTML"
        )


@media_router.message(commands=["screenview"])
async def cmd_screenview(message: Message) -> None:
    """Handle /screenview command to stream device screen"""
    try:
        # Get user and check permissions
        user_service = UserService()
        user = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        if not user.has_permission("screenview"):
            await message.reply(
                "❌ <b>Access Denied:</b> You don't have permission to view screen.",
                parse_mode="HTML"
            )
            return

        # Get device and check connection
        user_devices = await user_service.get_user_devices(user.id)
        if not user_devices:
            await message.reply(
                "❌ <b>No Devices:</b> No devices found. Use /auth <token> first.",
                parse_mode="HTML"
            )
            return

        device = user_devices[0]
        device_manager = DeviceManager()

        if not await device_manager.is_device_connected(device.device_id):
            await message.reply(
                "❌ <b>Device Offline:</b> Device not connected.",
                parse_mode="HTML"
            )
            return

        # Send initial message
        await message.reply(
            "📺 <b>Screen View Started</b>\n\n"
            "Your device screen will be streamed here.\n"
            "Send /screenshot to capture a still image.\n"
            "Note: Screen streaming requires an active connection.",
            parse_mode="HTML"
        )

        # Start screen streaming in background
        asyncio.create_task(_stream_screen(message, device, user))

        # Update user's last activity
        await user_service.update_last_activity(user.id)

    except Exception as e:
        logger.error(f"Error in screenview command: {e}")
        await message.reply(
            "❌ <b>Error:</b> An unexpected error occurred while starting screen view.",
            parse_mode="HTML"
        )


async def _stream_screen(message: Message, device, user: 'User') -> None:
    """Stream device screen in background"""
    try:
        device_manager = DeviceManager()
        stream_count = 0
        max_streams = 10  # Limit streaming to prevent abuse

        while stream_count < max_streams:
            if not await device_manager.is_device_connected(device.device_id):
                await message.reply(
                    "📺 <b>Screen View Stopped:</b> Device disconnected.",
                    parse_mode="HTML"
                )
                break

            # Request screenshot for streaming
            screenshot_data = await device_manager.request_screenshot(device.device_id)

            if screenshot_data:
                # Save temporarily
                temp_filename = f"screenview_{device.device_id[:8]}_{stream_count}.png"
                with open(temp_filename, "wb") as f:
                    f.write(screenshot_data)

                try:
                    # Send screenshot
                    await message.answer_photo(
                        open(temp_filename, "rb"),
                        caption=f"📺 Screen View {stream_count + 1}/10"
                    )
                finally:
                    # Clean up
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)

                stream_count += 1

                # Wait between captures (adjust as needed)
                await asyncio.sleep(3)
            else:
                await message.reply(
                    "📺 <b>Screen View Stopped:</b> Could not capture screen.",
                    parse_mode="HTML"
                )
                break

        if stream_count >= max_streams:
            await message.reply(
                "📺 <b>Screen View Completed:</b> Maximum streaming limit reached.",
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error in screen streaming: {e}")
        await message.reply(
            "📺 <b>Screen View Error:</b> Streaming stopped due to an error.",
            parse_mode="HTML"
        )