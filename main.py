"""
Delivery Monitoring Bot - Main Entry Point

This bot monitors Excel reports for delivery problems and notifies managers.

Usage:
    python main.py

The bot:
1. Downloads Excel file every N minutes from configured URL
2. Parses file for triggers (problem columns)
3. Sends notifications to registered managers
"""

import asyncio
import logging
import sys
import signal

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from database import db
from services.scheduler import setup_scheduler, run_check_now

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Flag for graceful shutdown
running = True


def handle_shutdown(signum, frame):
    """Handle shutdown signals."""
    global running
    logger.info("Shutdown signal received...")
    running = False


async def main() -> None:
    """
    Main function - entry point of the application.
    
    Sets up:
    1. Bot instance with token
    2. Scheduler for periodic Excel checks
    3. Runs checks automatically every N minutes
    
    Note: This bot does NOT use polling (no commands).
    It only sends notifications automatically.
    """
    global running
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Create bot instance
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    
    logger.info("=" * 60)
    logger.info("Delivery Monitoring Bot starting...")
    logger.info("=" * 60)
    
    # Initialize database
    await db.init_database()
    
    # Log configuration
    logger.info(f"Excel URL: {config.EXCEL_FILE_URL}")
    logger.info(f"Check interval: {config.CHECK_INTERVAL_MINUTES} minutes")
    logger.info(f"Users file: {config.USERS_JSON_PATH}")
    
    # Check if users file exists
    if config.USERS_JSON_PATH.exists():
        import json
        with open(config.USERS_JSON_PATH, "r", encoding="utf-8") as f:
            users = json.load(f)
        logger.info(f"Registered managers: {len(users)}")
    else:
        logger.warning(f"Users file not found: {config.USERS_JSON_PATH}")
    
    # Get bot info
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot: @{bot_info.username} (ID: {bot_info.id})")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
    
    logger.info("=" * 60)
    
    # Setup scheduler
    scheduler = setup_scheduler(bot)
    
    try:
        # Start scheduler
        scheduler.start()
        logger.info(f"Scheduler started - checking every {config.CHECK_INTERVAL_MINUTES} minute(s)")
        
        # Run first check immediately
        logger.info("Running initial check...")
        await run_check_now(bot)
        
        # Keep running until shutdown signal
        logger.info("Bot is running. Press Ctrl+C to stop.")
        while running:
            await asyncio.sleep(1)
        
    except asyncio.CancelledError:
        logger.info("Bot cancelled")
    finally:
        # Stop scheduler
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
        
        # Close bot session
        await bot.session.close()
        logger.info("Bot session closed")
        logger.info("Goodbye!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
