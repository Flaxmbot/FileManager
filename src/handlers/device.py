"""
Device management command handlers
"""

import asyncio
import os

from aiogram import Router
from aiogram.types import Message

from src.services.device_manager import DeviceManager
from src.services.device_service import DeviceService
from src.services.user_service import UserService
from src.utils.logger import get_logger

logger = get_logger(__name__)
device_router = Router()


@device_router.message(commands=["info"])
async def cmd_device_info(message: Message) -> None:
    """Handle /info command to get device information"""
    try:
        # Get user
        user_service = UserService()
        user = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        # Get user's devices
        device_service = DeviceService()
        user_devices = await device_service.get_user_devices(user.id)

        if not user_devices:
            await message.reply(
                "❌ <b>No Devices:</b> No devices found for your account.\n"
                "Use /auth <token> to connect a device first.",
                parse_mode="HTML"
            )
            return

        device = user_devices[0]  # Use first device
        device_manager = DeviceManager()

        # Get real-time device info if connected
        current_info = None
        if await device_manager.is_device_connected(device.device_id):
            current_info = await device_manager.request_device_info(device.device_id)

        # Format device information
        info_lines = [
            "📱 <b>Device Information</b>\n",
            f"🏷️ <b>Name:</b> {device.device_name}",
            f"🆔 <b>Device ID:</b> <code>{device.device_id}</code>",
            f"📊 <b>Status:</b> {device.status.value.title()}",
            f"🔗 <b>Connected:</b> {'Yes' if await device_manager.is_device_connected(device.device_id) else 'No'}",
        ]

        # Add stored device info
        if device.manufacturer:
            info_lines.append(f"🏭 <b>Manufacturer:</b> {device.manufacturer}")
        if device.model:
            info_lines.append(f"📱 <b>Model:</b> {device.model}")
        if device.brand:
            info_lines.append(f"🏷️ <b>Brand:</b> {device.brand}")
        if device.android_version:
            info_lines.append(f"🤖 <b>Android Version:</b> {device.android_version}")
        if device.api_level:
            info_lines.append(f"🔢 <b>API Level:</b> {device.api_level}")

        # Add real-time info if available
        if current_info:
            if "battery_level" in current_info:
                info_lines.append(f"🔋 <b>Battery:</b> {current_info['battery_level']}%")
            if "screen_resolution" in current_info:
                info_lines.append(f"📺 <b>Screen:</b> {current_info['screen_resolution']}")
            if "storage_info" in current_info:
                storage = current_info["storage_info"]
                info_lines.append(f"💾 <b>Storage:</b> {storage.get('available', 'N/A')} free")

        # Add timestamps
        if device.last_seen:
            info_lines.append(f"🕐 <b>Last Seen:</b> {device.last_seen.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if device.connected_at:
            info_lines.append(f"🔗 <b>Connected At:</b> {device.connected_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        # Add capabilities if available
        if device.capabilities:
            capabilities = device.capabilities
            cap_list = []
            if capabilities.get("file_operations"):
                cap_list.append("📁 Files")
            if capabilities.get("screenshot"):
                cap_list.append("📸 Screenshot")
            if capabilities.get("screenview"):
                cap_list.append("📺 Screen View")
            if capabilities.get("device_info"):
                cap_list.append("ℹ️ Device Info")

            if cap_list:
                info_lines.append(f"⚙️ <b>Capabilities:</b> {', '.join(cap_list)}")

        response = "\n".join(info_lines)

        await message.reply(response, parse_mode="HTML")

        # Update user's last activity
        await user_service.update_last_activity(user.id)

    except Exception as e:
        logger.error(f"Error in device_info command: {e}")
        await message.reply(
            "❌ <b>Error:</b> An unexpected error occurred while retrieving device information.",
            parse_mode="HTML"
        )


@device_router.message(commands=["list", "download", "upload", "delete", "search"])
async def cmd_file_operations(message: Message) -> None:
    """Handle file operation commands with device validation"""
    try:
        # Get user and validate device connection
        user_service = UserService()
        user = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        # Check user permissions based on command
        command = message.text.split()[0][1:]  # Remove '/' prefix

        permission_map = {
            "list": "read_files",
            "download": "read_files",
            "upload": "write_files",
            "delete": "delete_files",
            "search": "read_files"
        }

        required_permission = permission_map.get(command)
        if required_permission and not user.has_permission(required_permission):
            await message.reply(
                f"❌ <b>Access Denied:</b> You don't have permission to {command} files.",
                parse_mode="HTML"
            )
            return

        # Check device connection
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
                "❌ <b>Device Offline:</b> Your device is not connected.\n"
                "Please ensure your Android app is running and connected.",
                parse_mode="HTML"
            )
            return

        # Route to appropriate handler based on command
        if command == "list":
            # Extract path from command
            args = message.text.split()
            if len(args) < 2:
                await message.reply(
                    "❌ <b>Usage:</b> /list <path>\n\n"
                    "<b>Example:</b> /list /sdcard/Documents",
                    parse_mode="HTML"
                )
                return

            path = " ".join(args[1:])
            await message.reply(f"📁 <b>Listing files in:</b> {path}", parse_mode="HTML")

            file_list = await device_manager.request_file_list(device.device_id, path)

            if file_list and file_list.get("success"):
                files = file_list.get("files", [])
                if files:
                    response_lines = [f"📁 <b>Contents of {path}:</b>\n"]
                    for file_info in files[:15]:  # Limit output
                        file_type = "📁" if file_info.get("is_directory") else "📄"
                        file_name = file_info.get("name", "Unknown")
                        response_lines.append(f"{file_type} <b>{file_name}</b>")

                    response = "\n".join(response_lines)
                    await message.reply(response, parse_mode="HTML")
                else:
                    await message.reply("📁 <b>Directory is empty</b>", parse_mode="HTML")
            else:
                await message.reply(
                    "❌ <b>Error:</b> Could not retrieve file list.",
                    parse_mode="HTML"
                )

        elif command == "download":
            args = message.text.split()
            if len(args) < 2:
                await message.reply(
                    "❌ <b>Usage:</b> /download <file_path>",
                    parse_mode="HTML"
                )
                return

            file_path = " ".join(args[1:])
            await message.reply(f"⬇️ <b>Downloading:</b> {file_path}", parse_mode="HTML")

            file_data = await device_manager.request_file_download(device.device_id, file_path)

            if file_data:
                import os
                filename = os.path.basename(file_path)
                await message.reply_document(
                    (filename, file_data),
                    caption=f"📄 Downloaded: {filename}"
                )
            else:
                await message.reply(
                    "❌ <b>Download Failed:</b> Could not download the file.",
                    parse_mode="HTML"
                )

        elif command == "search":
            args = message.text.split()
            if len(args) < 2:
                await message.reply(
                    "❌ <b>Usage:</b> /search <query>",
                    parse_mode="HTML"
                )
                return

            query = " ".join(args[1:])
            await message.reply(f"🔍 <b>Searching for:</b> {query}", parse_mode="HTML")

            # Send search request to device
            search_message = {
                "action": "search_files",
                "query": query,
                "timestamp": asyncio.get_event_loop().time()
            }

            if await device_manager.send_message(device.device_id, search_message):
                await message.reply(
                    "🔍 <b>Search initiated.</b> Results will be sent when available.",
                    parse_mode="HTML"
                )
            else:
                await message.reply(
                    "❌ <b>Search Failed:</b> Could not initiate search.",
                    parse_mode="HTML"
                )

        # Update user's last activity
        await user_service.update_last_activity(user.id)

    except Exception as e:
        logger.error(f"Error in file_operations command: {e}")
        await message.reply(
            "❌ <b>Error:</b> An unexpected error occurred.",
            parse_mode="HTML"
        )