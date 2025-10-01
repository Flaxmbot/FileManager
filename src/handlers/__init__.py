"""
Bot command handlers package
"""

from aiogram import Dispatcher
from aiogram.filters import Command

from .auth import auth_router
from .device import device_router
from .files import files_router
from .media import media_router
from .start import start_router
from .common import common_router


async def setup_handlers(dp: Dispatcher) -> None:
    """Setup all bot handlers"""

    # Include all routers - this is the correct way in aiogram 3.x
    dp.include_router(start_router)
    dp.include_router(auth_router)
    dp.include_router(device_router)
    dp.include_router(files_router)
    dp.include_router(media_router)
    dp.include_router(common_router)