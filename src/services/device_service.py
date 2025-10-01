"""
Device service for managing device authentication and operations
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.models.device import Device, DeviceStatus, DeviceType
from src.models.user import User
from src.security.encryption import EncryptionManager
from src.services.device_manager import DeviceManager


class DeviceService:
    """Service for device management and authentication"""

    def __init__(self):
        self.encryption = EncryptionManager()
        self.device_manager = DeviceManager()

    async def authenticate_device(self, user_id: int, auth_token: str) -> Optional[Device]:
        """Authenticate device using token"""
        async for db in get_db():
            # Find device by auth token
            device = await self._get_device_by_auth_token(db, auth_token)

            if not device:
                return None

            # Verify token hasn't expired (tokens could have expiration logic)
            if not device.is_active:
                return None

            # Check if device belongs to user or can be claimed
            if device.user_id != user_id:
                # Allow claiming if device is not assigned
                if device.user_id is None:
                    device.user_id = user_id
                else:
                    return None  # Device already belongs to another user

            # Update device status and authentication
            device.status = DeviceStatus.ONLINE
            device.is_authenticated = True
            device.last_seen = datetime.utcnow()
            device.connected_at = datetime.utcnow()

            # Generate new auth token for security
            device.auth_token = self.encryption.generate_device_token()

            await db.commit()
            await db.refresh(device)

            return device

    async def _get_device_by_auth_token(self, db: AsyncSession, auth_token: str) -> Optional[Device]:
        """Get device by authentication token"""
        # In a real implementation, you'd hash the token for security
        # For now, we'll do a direct lookup
        result = await db.execute(
            "SELECT * FROM devices WHERE auth_token = :token AND is_active = true",
            {"token": auth_token}
        )
        return result.first()

    async def register_new_device(
        self,
        user_id: int,
        device_name: str,
        device_info: dict
    ) -> Device:
        """Register a new device for a user"""
        async for db in get_db():
            # Generate unique device ID
            device_id = f"device_{secrets.token_hex(16)}"

            # Create new device
            new_device = Device(
                user_id=user_id,
                device_id=device_id,
                device_name=device_name,
                device_type=DeviceType.ANDROID_DEVICE,
                status=DeviceStatus.OFFLINE,
                is_authenticated=False,
                auth_token=self.encryption.generate_device_token(),
                capabilities=device_info.get("capabilities", {}),
                android_version=device_info.get("android_version"),
                api_level=device_info.get("api_level"),
                manufacturer=device_info.get("manufacturer"),
                model=device_info.get("model"),
                brand=device_info.get("brand"),
                is_active=True
            )

            db.add(new_device)
            await db.commit()
            await db.refresh(new_device)

            return new_device

    async def update_device_status(self, device_id: str, status: DeviceStatus) -> bool:
        """Update device status"""
        async for db in get_db():
            device = await db.get(Device, device_id)
            if device:
                device.status = status
                if status == DeviceStatus.ONLINE:
                    device.last_seen = datetime.utcnow()
                    device.connected_at = datetime.utcnow()
                await db.commit()
                return True
            return False

    async def get_user_devices(self, user_id: int) -> list:
        """Get all devices for a user"""
        async for db in get_db():
            result = await db.execute(
                "SELECT * FROM devices WHERE user_id = :user_id AND is_active = true ORDER BY created_at DESC",
                {"user_id": user_id}
            )
            return result.fetchall()

    async def get_device_by_id(self, device_id: str) -> Optional[Device]:
        """Get device by device ID"""
        async for db in get_db():
            return await db.get(Device, device_id)

    async def deactivate_device(self, device_id: str) -> bool:
        """Deactivate a device"""
        async for db in get_db():
            device = await db.get(Device, device_id)
            if device:
                device.is_active = False
                device.status = DeviceStatus.OFFLINE
                await db.commit()
                return True
            return False

    async def update_device_info(self, device_id: str, device_info: dict) -> bool:
        """Update device information"""
        async for db in get_db():
            device = await db.get(Device, device_id)
            if device:
                # Update device info fields
                if "android_version" in device_info:
                    device.android_version = device_info["android_version"]
                if "api_level" in device_info:
                    device.api_level = device_info["api_level"]
                if "manufacturer" in device_info:
                    device.manufacturer = device_info["manufacturer"]
                if "model" in device_info:
                    device.model = device_info["model"]
                if "brand" in device_info:
                    device.brand = device_info["brand"]
                if "capabilities" in device_info:
                    device.capabilities = device_info["capabilities"]

                device.last_seen = datetime.utcnow()
                await db.commit()
                return True
            return False

    async def get_connected_devices_count(self) -> int:
        """Get count of currently connected devices"""
        async for db in get_db():
            result = await db.execute(
                "SELECT COUNT(*) FROM devices WHERE status = :status",
                {"status": DeviceStatus.ONLINE}
            )
            return result.scalar()

    async def cleanup_offline_devices(self) -> int:
        """Clean up devices that have been offline for too long"""
        async for db in get_db():
            # Mark devices as offline if they haven't been seen for more than 1 hour
            cutoff_time = datetime.utcnow() - timedelta(hours=1)

            result = await db.execute(
                "UPDATE devices SET status = :offline_status WHERE status = :online_status AND last_seen < :cutoff",
                {
                    "offline_status": DeviceStatus.OFFLINE,
                    "online_status": DeviceStatus.ONLINE,
                    "cutoff": cutoff_time
                }
            )

            await db.commit()
            return result.rowcount