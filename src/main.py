#!/usr/bin/env python3
"""
FileManager Telegram Bot - Main Application
Comprehensive remote device control and file management bot
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from src.config.settings import settings
from src.database.session import engine
from src.handlers import setup_handlers
from src.models.base import Base
from src.security.encryption import EncryptionManager
from src.services.device_manager import DeviceManager
from src.services.websocket_service import get_websocket_service
from src.utils.logger import setup_logging
from src.monitoring import run_health_server


async def run_telegram_bot() -> None:
    """Run the Telegram bot"""
    logger = logging.getLogger(__name__)

    # Initialize bot and dispatcher
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))

    # Use memory storage for FSM
    storage = MemoryStorage()
    logger.info("Using memory storage for FSM")

    dp = Dispatcher(storage=storage)

    # Setup handlers first
    await setup_handlers(dp)

    # Manual startup initialization
    logger.info("Initializing database and services...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await EncryptionManager.initialize()
    await DeviceManager.initialize()
    logger.info("Bot initialized successfully")

    # Start polling
    try:
        logger.info("Telegram bot started successfully")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("Telegram bot stopped by user")
    except Exception as e:
        logger.error(f"Telegram bot error: {e}")
        raise
    finally:
        logger.info("Shutting down bot...")
        await engine.dispose()
        await bot.session.close()


async def run_websocket_server() -> None:
    """Run the WebSocket server for device communication"""
    logger = logging.getLogger(__name__)

    try:
        websocket_service = get_websocket_service()
        await websocket_service.start_server(
            host=settings.API_HOST,
            port=settings.WS_PORT
        )
    except Exception as e:
        logger.error(f"WebSocket server error: {e}")
        raise


async def main() -> None:
    """Main application entry point - runs bot, health server, and WebSocket server"""
    # Setup logging
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("Starting FileManager Bot with health monitoring and WebSocket support...")

    try:
        # Create tasks for all services
        telegram_task = asyncio.create_task(run_telegram_bot())
        health_task = asyncio.create_task(run_health_server())
        websocket_task = asyncio.create_task(run_websocket_server())

        # Wait for any task to complete (all should run indefinitely)
        done, pending = await asyncio.wait(
            [telegram_task, health_task, websocket_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Check if any task raised an exception
        for task in done:
            try:
                await task
            except Exception as e:
                logger.error(f"Task failed with error: {e}")
                raise

    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        raise


if __name__ == "__main__":
    # Run the bot
    asyncio.run(main())