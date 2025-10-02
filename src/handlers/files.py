"""
File operations command handlers
"""

import os
from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from src.services.device_manager import DeviceManager
from src.services.user_service import UserService
from src.utils.logger import get_logger

logger = get_logger(__name__)
files_router = Router()


@files_router.message(Command("list"))
async def cmd_list_files(message: Message) -> None:
    """Handle /list command to list files and directories"""
    try:
        # Parse command arguments
        args = message.text.split()
        if len(args) < 2:
            await message.reply(
                "❌ <b>Usage:</b> /list [path]\n\n"
                "<b>Example:</b> /list /sdcard/Documents",
                parse_mode="HTML"
            )
            return

        path = " ".join(args[1:])  # Handle paths with spaces

        # Get user
        user_service = UserService()
        user = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        # Check if user has permission
        if not user.has_permission("read_files"):
            await message.reply(
                "❌ <b>Access Denied:</b> You don't have permission to list files.",
                parse_mode="HTML"
            )
            return

        # Get user's devices
        user_devices = await user_service.get_user_devices(user.id)
        if not user_devices:
            await message.reply(
                "❌ <b>No Devices:</b> No devices found for your account.\n"
                "Use /auth <token> to connect a device first.",
                parse_mode="HTML"
            )
            return

        # Use the first available device
        device = user_devices[0]
        device_manager = DeviceManager()

        if not await device_manager.is_device_connected(device.device_id):
            await message.reply(
                "❌ <b>Device Offline:</b> Your device is not connected.\n"
                "Please ensure your Android app is running and connected.",
                parse_mode="HTML"
            )
            return

        # Request file list from device
        await message.reply(f"📁 <b>Listing files in:</b> {path}", parse_mode="HTML")

        file_list = await device_manager.request_file_list(device.device_id, path)

        if not file_list or not file_list.get("success"):
            await message.reply(
                "❌ <b>Error:</b> Failed to retrieve file list.\n"
                "The path might not exist or be inaccessible.",
                parse_mode="HTML"
            )
            return

        files = file_list.get("files", [])
        if not files:
            await message.reply(
                "📁 <b>Directory is empty</b>",
                parse_mode="HTML"
            )
            return

        # Format file list with interactive buttons
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        response_lines = [f"📁 <b>Contents of:</b>\n<code>{path}</code>\n"]

        # Create navigation buttons
        keyboard = []

        for file_info in files[:15]:  # Limit to 15 files for better UX
            file_type = "📁" if file_info.get("is_directory") else "📄"
            file_name = file_info.get("name", "Unknown")
            file_size = file_info.get("size", 0)

            if file_info.get("is_directory"):
                # Add navigation button for directories
                button_text = f"📁 {file_name}"
                callback_data = f"browse:{path}:{file_name}"
                keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
                response_lines.append(f"📁 {file_name}/")
            else:
                size_str = format_file_size(file_size)
                response_lines.append(f"📄 {file_name} ({size_str})")

        if len(files) > 15:
            response_lines.append(f"\n... and {len(files) - 15} more files")

        response = "\n".join(response_lines)

        # Add parent directory button if not at root
        if path != "/" and path != "/sdcard":
            parent_path = "/".join(path.rstrip("/").split("/")[:-1]) or "/"
            keyboard.insert(0, [InlineKeyboardButton(text="⬅️ Parent Directory", callback_data=f"browse:{parent_path}:")])

        # Add back to home button
        keyboard.append([InlineKeyboardButton(text="🏠 Home", callback_data="browse:/sdcard/:")])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None

        # Split response if too long
        if len(response) > 4096:
            # Send as file if too long
            filename = f"file_list_{device.device_id[:8]}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"Contents of {path}:\n\n")
                for file_info in files:
                    file_type = "DIR" if file_info.get("is_directory") else "FILE"
                    file_name = file_info.get("name", "Unknown")
                    file_size = file_info.get("size", 0)
                    size_str = format_file_size(file_size)
                    f.write(f"{file_type} {file_name} ({size_str})\n")

            await message.reply_document(
                open(filename, "rb"),
                caption=f"📁 File list for {path}"
            )
            os.remove(filename)
        else:
            await message.reply(response, parse_mode="HTML", reply_markup=reply_markup)

        # Update user's last activity
        await user_service.update_last_activity(user.id)

    except Exception as e:
        logger.error(f"Error in list_files command: {e}")
        await message.reply(
            "❌ <b>Error:</b> An unexpected error occurred while listing files.",
            parse_mode="HTML"
        )


@files_router.message(Command("download"))
async def cmd_download_file(message: Message) -> None:
    """Handle /download command to download files from device"""
    try:
        # Parse command arguments
        args = message.text.split()
        if len(args) < 2:
            await message.reply(
                "❌ <b>Usage:</b> /download [file_path]\n\n"
                "<b>Example:</b> /download /sdcard/Documents/photo.jpg",
                parse_mode="HTML"
            )
            return

        file_path = " ".join(args[1:])

        # Get user and check permissions
        user_service = UserService()
        user = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        if not user.has_permission("read_files"):
            await message.reply(
                "❌ <b>Access Denied:</b> You don't have permission to download files.",
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

        # Request file download
        await message.reply(f"⬇️ <b>Downloading:</b> {file_path}", parse_mode="HTML")

        file_data = await device_manager.request_file_download(device.device_id, file_path)

        if not file_data:
            await message.reply(
                "❌ <b>Download Failed:</b> Could not download the file.\n"
                "The file might not exist or be inaccessible.",
                parse_mode="HTML"
            )
            return

        # Send file to user
        filename = os.path.basename(file_path)
        await message.reply_document(
            (filename, file_data),
            caption=f"📄 Downloaded: {filename}"
        )

        # Update activity
        await user_service.update_last_activity(user.id)

    except Exception as e:
        logger.error(f"Error in download_file command: {e}")
        await message.reply(
            "❌ <b>Error:</b> An unexpected error occurred while downloading the file.",
            parse_mode="HTML"
        )


@files_router.message(Command("delete"))
async def cmd_delete_file(message: Message) -> None:
    """Handle /delete command to delete files from device"""
    try:
        # Parse command arguments
        args = message.text.split()
        if len(args) < 2:
            await message.reply(
                "❌ <b>Usage:</b> /delete [file_path]\n\n"
                "<b>Example:</b> /delete /sdcard/Documents/old_file.txt",
                parse_mode="HTML"
            )
            return

        file_path = " ".join(args[1:])

        # Get user and check permissions
        user_service = UserService()
        user = await user_service.get_or_create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        if not user.has_permission("delete_files"):
            await message.reply(
                "❌ <b>Access Denied:</b> You don't have permission to delete files.",
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

        # Confirm deletion for safety
        await message.reply(
            f"⚠️ <b>Delete Confirmation:</b>\n\n"
            f"Are you sure you want to delete:\n"
            f"<code>{file_path}</code>\n\n"
            f"Reply with <b>YES</b> to confirm deletion.",
            parse_mode="HTML"
        )

        # Update activity
        await user_service.update_last_activity(user.id)

    except Exception as e:
        logger.error(f"Error in delete_file command: {e}")
        await message.reply(
            "❌ <b>Error:</b> An unexpected error occurred.",
            parse_mode="HTML"
        )


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_index = 0
    while size_bytes >= 1024 and size_index < len(size_names) - 1:
        size_bytes /= 1024.0
        size_index += 1

    return f"{size_bytes:.1f} {size_names[size_index]}"


@files_router.callback_query(lambda c: c.data.startswith("browse:"))
async def handle_file_browse(callback: CallbackQuery):
    """Handle file browsing via inline keyboard"""
    try:
        # Parse callback data: "browse:current_path:target_name"
        parts = callback.data.split(":", 2)
        if len(parts) >= 3:
            current_path = parts[1]
            target_name = parts[2]
            new_path = f"{current_path.rstrip('/')}/{target_name}".replace("//", "/")
            if not new_path.startswith("/"):
                new_path = "/" + new_path
        else:
            new_path = "/sdcard/"

        # Get user and validate permissions
        user_service = UserService()
        user = await user_service.get_or_create_user(
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name
        )

        if not user.has_permission("read_files"):
            await callback.answer("❌ Access denied", show_alert=True)
            return

        # Get device and check connection
        user_devices = await user_service.get_user_devices(user.id)
        if not user_devices:
            await callback.message.edit_text(
                "❌ <b>No Devices:</b> No devices found. Use /auth [token] first.",
                parse_mode="HTML",
                reply_markup=None
            )
            await callback.answer()
            return

        device = user_devices[0]
        device_manager = DeviceManager()

        if not await device_manager.is_device_connected(device.device_id):
            await callback.message.edit_text(
                "❌ <b>Device Offline:</b> Device not connected.",
                parse_mode="HTML",
                reply_markup=None
            )
            await callback.answer()
            return

        # Request file list from device
        await callback.message.edit_text(f"📁 <b>Loading:</b> {new_path}", parse_mode="HTML")

        file_list = await device_manager.request_file_list(device.device_id, new_path)

        if not file_list or not file_list.get("success"):
            await callback.message.edit_text(
                "❌ <b>Error:</b> Failed to retrieve file list.\n"
                "The path might not exist or be inaccessible.",
                parse_mode="HTML",
                reply_markup=None
            )
            await callback.answer()
            return

        files = file_list.get("files", [])
        if not files:
            await callback.message.edit_text(
                f"📁 <b>Directory is empty</b>\n\n<code>{new_path}</code>",
                parse_mode="HTML",
                reply_markup=None
            )
            await callback.answer()
            return

        # Format file list with interactive buttons
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        response_lines = [f"📁 <b>Contents of:</b>\n<code>{new_path}</code>\n"]
        keyboard = []

        for file_info in files[:15]:  # Limit to 15 files for better UX
            file_type = "📁" if file_info.get("is_directory") else "📄"
            file_name = file_info.get("name", "Unknown")
            file_size = file_info.get("size", 0)

            if file_info.get("is_directory"):
                # Add navigation button for directories
                button_text = f"📁 {file_name}"
                callback_data = f"browse:{new_path}:{file_name}"
                keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
                response_lines.append(f"📁 {file_name}/")
            else:
                size_str = format_file_size(file_size)
                response_lines.append(f"📄 {file_name} ({size_str})")

        if len(files) > 15:
            response_lines.append(f"\n... and {len(files) - 15} more files")

        response = "\n".join(response_lines)

        # Add parent directory button if not at root
        if new_path != "/" and new_path != "/sdcard":
            parent_path = "/".join(new_path.rstrip("/").split("/")[:-1]) or "/"
            keyboard.insert(0, [InlineKeyboardButton(text="⬅️ Parent Directory", callback_data=f"browse:{parent_path}:")])

        # Add back to home button
        keyboard.append([InlineKeyboardButton(text="🏠 Home", callback_data="browse:/sdcard/:")])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        await callback.message.edit_text(response, parse_mode="HTML", reply_markup=reply_markup)
        await callback.answer()

    except Exception as e:
        print(f"Error in file browse handler: {e}")
        import traceback
        traceback.print_exc()
        await callback.message.edit_text(
            "❌ <b>Error:</b> Failed to browse files.",
            parse_mode="HTML",
            reply_markup=None
        )
        await callback.answer()