"""
Scheduler service.

Runs periodic task to check Excel file for new triggers.
Downloads file, parses it, and sends notifications.
"""

import logging
from pathlib import Path

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

import config
from services.excel_downloader import download_excel_file, cleanup_temp_files, DownloadError
from services.excel_parser import parse_excel_file
from bot.notifications import send_notifications_batch

logger = logging.getLogger(__name__)


async def check_excel_for_triggers(bot: Bot) -> None:
    """
    Main scheduled task: check Excel file for new triggers.
    
    This function runs every N minutes (configured in config.py).
    
    Steps:
    1. Download Excel file from URL
    2. Parse file and extract rows with triggers
    3. Send notifications to managers
    4. Clean up temporary files
    
    Args:
        bot: Telegram Bot instance for sending notifications
    """
    logger.info("=" * 50)
    logger.info("Starting scheduled check for delivery problems...")
    
    downloaded_file: Path = None
    
    try:
        # Step 1: Download Excel file
        logger.info(f"Downloading from: {config.EXCEL_FILE_URL}")
        downloaded_file = await download_excel_file()
        
        # Step 2: Parse Excel file
        triggers = parse_excel_file(downloaded_file)
        
        if not triggers:
            logger.info("No triggers found in file")
            return
        
        logger.info(f"Found {len(triggers)} triggers to process")
        
        # Step 3: Send notifications
        stats = await send_notifications_batch(bot, triggers)
        
        # Log results
        logger.info(
            f"Notification results: "
            f"sent={stats['sent']}, "
            f"skipped={stats['skipped']}, "
            f"not_found={stats['not_found']}, "
            f"failed={stats['failed']}"
        )
        
    except DownloadError as e:
        logger.error(f"Failed to download Excel file: {e}")
        
    except Exception as e:
        logger.error(f"Error during scheduled check: {e}", exc_info=True)
        
    finally:
        # Step 4: Cleanup
        cleanup_temp_files(keep_last=3)
        
        # Delete current file if it exists
        if downloaded_file and downloaded_file.exists():
            try:
                downloaded_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")
        
        logger.info("Scheduled check completed")
        logger.info("=" * 50)


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """
    Set up and configure the scheduler.
    
    Creates an AsyncIOScheduler that runs check_excel_for_triggers
    every N minutes (from config).
    
    Args:
        bot: Telegram Bot instance
        
    Returns:
        Configured AsyncIOScheduler (not started)
    """
    from datetime import datetime, timedelta
    
    scheduler = AsyncIOScheduler()
    
    # Calculate first run time (1 minute from now, since we run immediate check)
    first_run = datetime.now() + timedelta(minutes=config.CHECK_INTERVAL_MINUTES)
    
    # Add the main job
    scheduler.add_job(
        check_excel_for_triggers,
        trigger=IntervalTrigger(minutes=config.CHECK_INTERVAL_MINUTES),
        args=[bot],
        id="excel_check",
        name="Check Excel for delivery problems",
        replace_existing=True,
        next_run_time=first_run  # First scheduled run after interval
    )
    
    logger.info(
        f"Scheduler configured: checking every {config.CHECK_INTERVAL_MINUTES} minute(s)"
    )
    logger.info(f"Next scheduled check at: {first_run.strftime('%H:%M:%S')}")
    
    return scheduler


async def run_check_now(bot: Bot) -> None:
    """
    Run an immediate check (for testing or manual trigger).
    
    Args:
        bot: Telegram Bot instance
    """
    logger.info("Running immediate check...")
    await check_excel_for_triggers(bot)

