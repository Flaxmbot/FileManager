"""
User model for authentication and authorization
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, String
from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class Permission(str, Enum):
    """User permissions"""
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    DELETE_FILES = "delete_files"
    SCREENSHOT = "screenshot"
    SCREENVIEW = "screenview"
    DEVICE_INFO = "device_info"
    ADMIN_ACCESS = "admin_access"


class User(BaseModel):
    """User model for bot authentication"""

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False,
        comment="Telegram user ID"
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(32),
        index=True,
        comment="Telegram username"
    )
    first_name: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="User's first name"
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="User's last name"
    )
    role: Mapped[UserRole] = mapped_column(
        String(20),
        default=UserRole.USER,
        nullable=False,
        comment="User role"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether user is active"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether user is verified"
    )
    language_code: Mapped[Optional[str]] = mapped_column(
        String(10),
        comment="User's language code"
    )
    last_activity: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        comment="Last activity timestamp"
    )

    # Relationships
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    operation_logs = relationship("OperationLog", back_populates="user", cascade="all, delete-orphan")

    @property
    def permissions(self) -> List[Permission]:
        """Get user permissions based on role"""
        if self.role == UserRole.ADMIN:
            return [permission for permission in Permission]
        elif self.role == UserRole.USER:
            return [
                Permission.READ_FILES,
                Permission.WRITE_FILES,
                Permission.DELETE_FILES,
                Permission.SCREENSHOT,
                Permission.SCREENVIEW,
                Permission.DEVICE_INFO,
            ]
        else:  # GUEST
            return [
                Permission.READ_FILES,
                Permission.DEVICE_INFO,
            ]

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions

    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == UserRole.ADMIN

    def get_display_name(self) -> str:
        """Get display name for user"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return f"@{self.username}"
        else:
            return f"User {self.telegram_id}"

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"