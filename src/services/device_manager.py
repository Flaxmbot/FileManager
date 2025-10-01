"""
Device manager for handling Android device connections
"""

import asyncio
import json
from typing import Dict, List, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from src.config.settings import settings
from src.models.device import Device, DeviceStatus
from src.security.encryption import EncryptionManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DeviceManager:
    """Manager for Android device connections"""

    _instance = None
    _connected_devices: Dict[str, websockets.WebSocketServerProtocol] = {}
    _device_info: Dict[str, Dict] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeviceManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(cls):
        """Initialize device manager"""
        instance = cls()
        logger.info("Device manager initialized")

    async def register_device(
        self,
        device_id: str,
        websocket: websockets.WebSocketServerProtocol,
        device_info: Dict
    ) -> bool:
        """Register a new device connection"""
        try:
            self._connected_devices[device_id] = websocket
            self._device_info[device_id] = device_info

            logger.info(f"Device registered: {device_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register device {device_id}: {e}")
            return False

    async def unregister_device(self, device_id: str) -> None:
        """Unregister a device connection"""
        try:
            if device_id in self._connected_devices:
                del self._connected_devices[device_id]
            if device_id in self._device_info:
                del self._device_info[device_id]

            logger.info(f"Device unregistered: {device_id}")
        except Exception as e:
            logger.error(f"Failed to unregister device {device_id}: {e}")

    async def is_device_connected(self, device_id: str) -> bool:
        """Check if device is connected"""
        return device_id in self._connected_devices

    async def send_message(self, device_id: str, message: Dict) -> bool:
        """Send message to device"""
        try:
            if not await self.is_device_connected(device_id):
                logger.warning(f"Device {device_id} not connected")
                return False

            websocket = self._connected_devices[device_id]

            # Encrypt message if device supports encryption
            if device_id in self._device_info:
                device_info = self._device_info[device_id]
                if device_info.get("encryption_enabled"):
                    encryption = EncryptionManager()
                    message_str = json.dumps(message)
                    encrypted = encryption.encrypt_message(message_str)
                    message = {"encrypted": True, "data": encrypted.decode('latin1')}

            await websocket.send(json.dumps(message))
            return True

        except ConnectionClosed:
            logger.warning(f"Connection closed for device {device_id}")
            await self.unregister_device(device_id)
            return False
        except Exception as e:
            logger.error(f"Failed to send message to device {device_id}: {e}")
            return False

    async def request_file_list(self, device_id: str, path: str) -> Optional[Dict]:
        """Request file list from device"""
        message = {
            "action": "list_files",
            "path": path,
            "timestamp": asyncio.get_event_loop().time()
        }

        if await self.send_message(device_id, message):
            try:
                websocket = self._connected_devices[device_id]
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=settings.DEVICE_TIMEOUT
                )
                return json.loads(response)
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for file list from device {device_id}")
            except Exception as e:
                logger.error(f"Error receiving file list from device {device_id}: {e}")

        return None

    async def request_file_download(self, device_id: str, file_path: str) -> Optional[bytes]:
        """Request file download from device"""
        message = {
            "action": "download_file",
            "path": file_path,
            "timestamp": asyncio.get_event_loop().time()
        }

        if await self.send_message(device_id, message):
            try:
                websocket = self._connected_devices[device_id]
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=settings.DEVICE_TIMEOUT
                )

                response_data = json.loads(response)

                if response_data.get("success"):
                    # File data is base64 encoded
                    import base64
                    file_data = base64.b64decode(response_data["data"])
                    return file_data

            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for file download from device {device_id}")
            except Exception as e:
                logger.error(f"Error downloading file from device {device_id}: {e}")

        return None

    async def request_screenshot(self, device_id: str) -> Optional[bytes]:
        """Request screenshot from device"""
        message = {
            "action": "screenshot",
            "timestamp": asyncio.get_event_loop().time()
        }

        if await self.send_message(device_id, message):
            try:
                websocket = self._connected_devices[device_id]
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=settings.DEVICE_TIMEOUT
                )

                response_data = json.loads(response)

                if response_data.get("success"):
                    # Screenshot data is base64 encoded
                    import base64
                    screenshot_data = base64.b64decode(response_data["data"])
                    return screenshot_data

            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for screenshot from device {device_id}")
            except Exception as e:
                logger.error(f"Error getting screenshot from device {device_id}: {e}")

        return None

    async def request_device_info(self, device_id: str) -> Optional[Dict]:
        """Request device information"""
        message = {
            "action": "device_info",
            "timestamp": asyncio.get_event_loop().time()
        }

        if await self.send_message(device_id, message):
            try:
                websocket = self._connected_devices[device_id]
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=settings.DEVICE_TIMEOUT
                )
                return json.loads(response)
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for device info from device {device_id}")
            except Exception as e:
                logger.error(f"Error getting device info from device {device_id}: {e}")

        return None

    async def get_connected_devices(self) -> List[str]:
        """Get list of connected device IDs"""
        return list(self._connected_devices.keys())

    async def get_device_info(self, device_id: str) -> Optional[Dict]:
        """Get device information"""
        return self._device_info.get(device_id)

    async def broadcast_message(self, message: Dict) -> int:
        """Broadcast message to all connected devices"""
        sent_count = 0
        connected_devices = await self.get_connected_devices()

        for device_id in connected_devices:
            if await self.send_message(device_id, message):
                sent_count += 1

        return sent_count