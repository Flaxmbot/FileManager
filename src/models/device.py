"""
Device model for managing connected Android devices
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.sql import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel


class DeviceStatus(str, Enum):
    """Device connection status"""
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    DISCONNECTING = "disconnecting"
    UNAUTHORIZED = "unauthorized"


class DeviceType(str, Enum):
    """Device type enumeration"""
    PHONE = "phone"
    TABLET = "tablet"
    ANDROID_DEVICE = "android_device"


class Device(BaseModel):
    """Device model for connected Android devices"""

    __tablename__ = "devices"

    user_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
        comment="User who owns this device"
    )
    device_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique device identifier"
    )
    device_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable device name"
    )
    device_type: Mapped[DeviceType] = mapped_column(
        String(20),
        default=DeviceType.ANDROID_DEVICE,
        nullable=False,
        comment="Type of device"
    )
    status: Mapped[DeviceStatus] = mapped_column(
        String(20),
        default=DeviceStatus.OFFLINE,
        nullable=False,
        comment="Current device status"
    )

    # Device information
    android_version: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Android version"
    )
    api_level: Mapped[Optional[int]] = mapped_column(
        comment="Android API level"
    )
    manufacturer: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Device manufacturer"
    )
    model: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Device model"
    )
    brand: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Device brand"
    )

    # Connection information
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        comment="Device IP address"
    )
    port: Mapped[Optional[int]] = mapped_column(
        comment="Device port"
    )
    websocket_url: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="WebSocket connection URL"
    )

    # Security
    public_key: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Device public key for encryption"
    )
    is_authenticated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether device is authenticated"
    )
    auth_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="Authentication token"
    )

    # Capabilities
    capabilities: Mapped[Optional[Dict]] = mapped_column(
        JSON,
        comment="Device capabilities and supported features"
    )

    # Timestamps
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Last time device was seen online"
    )
    connected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="When device was last connected"
    )

    # Settings
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether device is active"
    )
    max_connections: Mapped[int] = mapped_column(
        default=3,
        nullable=False,
        comment="Maximum concurrent connections"
    )

    # Relationships
    user = relationship("User", back_populates="devices")
    sessions = relationship("DeviceSession", back_populates="device", cascade="all, delete-orphan")
    operation_logs = relationship("OperationLog", back_populates="device", cascade="all, delete-orphan")

    def is_online(self) -> bool:
        """Check if device is currently online"""
        return self.status == DeviceStatus.ONLINE

    def can_connect(self) -> bool:
        """Check if device can accept new connections"""
        return (
            self.is_active and
            self.is_authenticated and
            self.status in [DeviceStatus.ONLINE, DeviceStatus.OFFLINE]
        )

    def get_connection_info(self) -> Dict:
        """Get device connection information"""
        return {
            "device_id": self.device_id,
            "websocket_url": self.websocket_url,
            "ip_address": self.ip_address,
            "port": self.port,
            "status": self.status.value,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
        }

    def update_last_seen(self):
        """Update last seen timestamp"""
        self.last_seen = datetime.utcnow()

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, device_id={self.device_id}, name={self.device_name})>"