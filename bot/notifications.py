"""
Notification service.

Sends notifications to managers via Telegram.
Reads manager data from registration_bot/users.json file.
"""

import json
import logging
from typing import Optional

from aiogram import Bot

import config
from database import db
from database.models import User
from services.excel_parser import TriggerRow

logger = logging.getLogger(__name__)


def load_users_from_json() -> dict[str, int]:
    """
    Load users from registration_bot/users.json file.
    
    Returns:
        Dictionary mapping normalized FIO -> Telegram ID
        
    File format expected:
    {
        "telegram_id": {
            "user_id": "telegram_id",
            "fio": "Фамилия Имя Отчество"
        }
    }
    """
    try:
        if not config.USERS_JSON_PATH.exists():
            logger.error(f"Users file not found: {config.USERS_JSON_PATH}")
            return {}
        
        with open(config.USERS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Build FIO -> Telegram ID mapping
        users_map: dict[str, int] = {}
        
        for telegram_id, user_info in data.items():
            fio = user_info.get("fio", "")
            if fio:
                # Normalize FIO (ё -> е) for matching
                fio_normalized = User.normalize_fio(fio)
                users_map[fio_normalized] = int(telegram_id)
        
        logger.info(f"Loaded {len(users_map)} users from {config.USERS_JSON_PATH}")
        return users_map
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing users.json: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        return {}


async def get_telegram_id_for_manager(manager_fio: str) -> Optional[int]:
    """
    Get Telegram ID for a manager by their FIO.
    
    Looks up manager in registration_bot/users.json file.
    
    Args:
        manager_fio: Manager's full name from Excel
        
    Returns:
        Telegram ID if found, None otherwise
    """
    # Load users from JSON file (reload each time to get fresh data)
    users_map = load_users_from_json()
    
    # Normalize FIO for matching
    fio_normalized = User.normalize_fio(manager_fio)
    
    # Look up in users map
    telegram_id = users_map.get(fio_normalized)
    
    if telegram_id:
        logger.debug(f"Found manager: {manager_fio} -> {telegram_id}")
    else:
        logger.debug(f"Manager not found in users.json: {manager_fio}")
    
    return telegram_id


def get_notification_message(trigger: TriggerRow) -> str:
    """
    Get notification message text based on trigger type.
    
    Args:
        trigger: TriggerRow object with trigger information
        
    Returns:
        Formatted notification message
    """
    # Base message from config
    if trigger.trigger_type == 1:
        base_message = config.MESSAGE_TRIGGER_1
    else:
        base_message = config.MESSAGE_TRIGGER_2
    
    # Add order details
    # Truncate order_info if too long
    order_short = trigger.order_info[:50] + "..." if len(trigger.order_info) > 50 else trigger.order_info
    
    full_message = (
        f"{base_message}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 **Заказ:** {order_short}\n"
        f"👤 **Менеджер:** {trigger.manager_fio}\n"
    )
    
    return full_message


async def send_notification(
    bot: Bot,
    trigger: TriggerRow
) -> bool:
    """
    Send notification to manager about a delivery problem.
    
    Args:
        bot: Telegram Bot instance
        trigger: TriggerRow with trigger information
        
    Returns:
        True if notification was sent, False otherwise
    """
    # Get Telegram ID for this manager
    telegram_id = await get_telegram_id_for_manager(trigger.manager_fio)
    
    if not telegram_id:
        logger.warning(
            f"Manager not registered in MAKON_id_bot: {trigger.manager_fio}"
        )
        return False
    
    # Get message text
    message_text = get_notification_message(trigger)
    
    try:
        # Send message
        await bot.send_message(
            chat_id=telegram_id,
            text=message_text,
            parse_mode="Markdown"
        )
        
        logger.info(
            f"Notification sent to {trigger.manager_fio} "
            f"(ID: {telegram_id}), trigger type: {trigger.trigger_type}"
        )
        return True
        
    except Exception as e:
        logger.error(
            f"Failed to send notification to {telegram_id}: {e}"
        )
        return False


async def send_notifications_batch(
    bot: Bot,
    triggers: list[TriggerRow]
) -> dict:
    """
    Send notifications for a batch of triggers.
    
    Checks if each row was already processed and skips duplicates.
    
    Args:
        bot: Telegram Bot instance
        triggers: List of TriggerRow objects
        
    Returns:
        Dictionary with statistics:
        - sent: number of notifications sent
        - skipped: number of already processed
        - not_found: number of managers not in users.json
        - failed: number of send failures
    """
    stats = {
        "sent": 0,
        "skipped": 0,
        "not_found": 0,
        "failed": 0
    }
    
    for trigger in triggers:
        # Check if already processed
        if await db.is_row_processed(trigger.row_hash):
            logger.debug(f"Row already processed: {trigger.row_hash}")
            stats["skipped"] += 1
            continue
        
        # Get Telegram ID
        telegram_id = await get_telegram_id_for_manager(trigger.manager_fio)
        
        if not telegram_id:
            logger.warning(f"Manager not in users.json: {trigger.manager_fio}")
            stats["not_found"] += 1
            # Still mark as processed to avoid repeated warnings
            await db.mark_row_processed(
                trigger.row_hash,
                trigger.trigger_type,
                trigger.order_info
            )
            continue
        
        # Send notification
        success = await send_notification(bot, trigger)
        
        if success:
            stats["sent"] += 1
            # Mark as processed
            await db.mark_row_processed(
                trigger.row_hash,
                trigger.trigger_type,
                trigger.order_info
            )
        else:
            stats["failed"] += 1
    
    return stats
