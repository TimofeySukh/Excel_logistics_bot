"""
Telegram bot handlers.

Handles user commands:
- /start - Welcome message
- /check - Manual trigger check (admin only)
- /help - Show help message
"""

import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart

import config

logger = logging.getLogger(__name__)

# Create router for handlers
router = Router()

# Admin user IDs who can run manual checks (add your Telegram IDs here)
ADMIN_IDS = [123456789, 987654321]


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Handle /start command.
    
    Shows welcome message. Registration happens in id_bot, not here.
    """
    await message.answer(
        "👋 Добро пожаловать в систему уведомлений о доставке!\n\n"
        "Этот бот автоматически отправляет уведомления менеджерам "
        "о проблемах с доставкой заказов.\n\n"
        "📝 **Важно:** Регистрация менеджеров происходит через отдельный бот регистрации\n\n"
        "Используйте /help для справки.",
        parse_mode="Markdown"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    Handle /help command.
    
    Shows available commands and bot description.
    """
    await message.answer(
        "📚 **Помощь по боту**\n\n"
        "Этот бот автоматически отправляет уведомления менеджерам о проблемах с доставкой.\n\n"
        "**Как это работает:**\n"
        f"1. Бот проверяет Excel файл каждые {config.CHECK_INTERVAL_MINUTES} мин\n"
        "2. Ищет отметки в колонках 'Проблема 1' и 'Проблема 2'\n"
        "3. Находит ответственного менеджера по ФИО из колонки заказа\n"
        "4. Отправляет уведомление ТОЛЬКО этому менеджеру\n\n"
        "Бот работает полностью автоматически. Просто ставьте отметки в Excel!\n\n"
        "📝 Для регистрации обратитесь к администратору",
        parse_mode="Markdown"
    )


@router.message()
async def unknown_message(message: Message) -> None:
    """
    Handle any other message.
    
    Prompts user to use /help.
    """
    await message.answer(
        "🤔 Бот работает автоматически.\n\n"
        "Используйте /help для справки."
    )
