"""
User service for managing bot users
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_db
from src.models.user import User, UserRole
from src.security.encryption import EncryptionManager


class UserService:
    """Service for user management operations"""

    def __init__(self):
        self.encryption = EncryptionManager()

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> User:
        """Get existing user or create new one"""
        async for db in get_db():
            # Try to find existing user
            user = await self.get_user_by_telegram_id(db, telegram_id)

            if user:
                # Update user information if needed
                updated = False
                if username and user.username != username:
                    user.username = username
                    updated = True
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    updated = True
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                    updated = True
                if language_code and user.language_code != language_code:
                    user.language_code = language_code
                    updated = True

                if updated:
                    await db.commit()

                return user

            # Create new user
            new_user = User(
                telegram_id=str(telegram_id),
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                role=UserRole.USER,
                is_active=True,
                is_verified=False
            )

            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)

            return new_user

    async def get_user_by_telegram_id(self, db: AsyncSession, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        return await db.get(User, str(telegram_id))

    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by database ID"""
        return await db.get(User, user_id)

    async def update_last_activity(self, user_id: int) -> None:
        """Update user's last activity timestamp"""
        async for db in get_db():
            user = await db.get(User, user_id)
            if user:
                user.last_activity = datetime.utcnow()
                await db.commit()

    async def verify_user(self, user_id: int) -> bool:
        """Verify user (mark as verified)"""
        async for db in get_db():
            user = await db.get(User, user_id)
            if user:
                user.is_verified = True
                await db.commit()
                return True
            return False

    async def set_user_role(self, user_id: int, role: UserRole) -> bool:
        """Set user role"""
        async for db in get_db():
            user = await db.get(User, user_id)
            if user:
                user.role = role
                await db.commit()
                return True
            return False

    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user"""
        async for db in get_db():
            user = await db.get(User, user_id)
            if user:
                user.is_active = False
                await db.commit()
                return True
            return False

    async def get_active_users_count(self) -> int:
        """Get count of active users"""
        async for db in get_db():
            result = await db.execute(
                "SELECT COUNT(*) FROM users WHERE is_active = true"
            )
            return result.scalar()

    async def get_verified_users_count(self) -> int:
        """Get count of verified users"""
        async for db in get_db():
            result = await db.execute(
                "SELECT COUNT(*) FROM users WHERE is_verified = true"
            )
            return result.scalar()

    async def get_user_devices(self, user_id: int) -> list:
        """Get all devices for a user"""
        async for db in get_db():
            user = await db.get(User, user_id)
            if user:
                return user.devices
            return []