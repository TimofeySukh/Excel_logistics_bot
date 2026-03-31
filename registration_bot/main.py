"""
Manager Registration Bot

This bot allows managers to register their Telegram ID by entering their FIO.
Features:
- Loads manager list from Excel file
- Fuzzy matching for typos (searches by parts of FIO)
- Suggests similar names with inline buttons
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional
import pandas as pd

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file!")

# Paths
USERS_FILE = Path(__file__).parent / "users.json"
EXCEL_FILE = os.getenv("EXCEL_FILE_PATH", Path(__file__).parent.parent / "data" / "managers.xlsx")

# Initialize bot
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)


# FSM States
class UserRegistration(StatesGroup):
    waiting_for_fio = State()


def normalize_fio(text: str) -> str:
    """Normalize FIO: replace ё with е, strip whitespace"""
    return text.replace('ё', 'е').replace('Ё', 'Е').strip()


def load_managers_from_excel() -> list[str]:
    """Load all unique managers from Excel file"""
    try:
        if not EXCEL_FILE.exists():
            print(f"⚠️ Excel file not found: {EXCEL_FILE}")
            return []
        
        df = pd.read_excel(EXCEL_FILE)
        managers = df.iloc[6:, 9].dropna().unique()
        
        # Filter out headers and normalize
        result = []
        for m in managers:
            m_str = str(m).strip()
            if m_str and m_str != "Менеджер" and m_str != "nan":
                result.append(normalize_fio(m_str))
        
        print(f"📋 Loaded {len(result)} managers from Excel")
        return result
    except Exception as e:
        print(f"❌ Error loading managers: {e}")
        return []


def load_users() -> dict:
    """Load registered users from JSON"""
    if USERS_FILE.exists():
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_users(users_data: dict) -> None:
    """Save users to JSON"""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_data, f, ensure_ascii=False, indent=2)


def find_similar_managers(input_fio: str, managers: list[str], max_results: int = 5) -> list[str]:
    """
    Find managers similar to input FIO.
    
    Searches by matching parts of FIO (surname, name, patronymic).
    Returns list of possible matches.
    """
    input_normalized = normalize_fio(input_fio).lower()
    input_parts = input_normalized.split()
    
    # First check for exact match
    for m in managers:
        if normalize_fio(m).lower() == input_normalized:
            return [m]  # Exact match found
    
    # Score each manager by matching parts
    scored = []
    
    for manager in managers:
        manager_normalized = normalize_fio(manager).lower()
        manager_parts = manager_normalized.split()
        
        score = 0
        matched_parts = []
        
        for input_part in input_parts:
            if len(input_part) < 2:  # Skip very short parts
                continue
                
            for manager_part in manager_parts:
                # Exact part match
                if input_part == manager_part:
                    score += 10
                    matched_parts.append(manager_part)
                    break
                # Partial match (input is substring of manager part)
                elif input_part in manager_part or manager_part in input_part:
                    score += 5
                    matched_parts.append(manager_part)
                    break
                # First 3 letters match (for typos)
                elif len(input_part) >= 3 and len(manager_part) >= 3:
                    if input_part[:3] == manager_part[:3]:
                        score += 3
                        matched_parts.append(manager_part)
                        break
        
        if score > 0:
            scored.append((score, manager, len(matched_parts)))
    
    # Sort by score (descending), then by number of matched parts
    scored.sort(key=lambda x: (x[0], x[2]), reverse=True)
    
    # Return top results
    return [m for _, m, _ in scored[:max_results]]


def create_manager_keyboard(managers: list[str]) -> InlineKeyboardMarkup:
    """Create inline keyboard with manager options"""
    buttons = []
    for manager in managers:
        # Truncate long names for button text
        display_name = manager if len(manager) <= 40 else manager[:37] + "..."
        buttons.append([
            InlineKeyboardButton(
                text=display_name,
                callback_data=f"select:{manager[:50]}"  # Callback data limit
            )
        ])
    
    # Add cancel button
    buttons.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Global managers list (loaded on startup)
MANAGERS_LIST: list[str] = []


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Handle /start command"""
    user_id = str(message.from_user.id)
    users = load_users()
    
    if user_id in users:
        fio = users[user_id].get("fio", "")
        await message.answer(
            f"С возвращением! 👋\n\n"
            f"Вы зарегистрированы как:\n**{fio}**\n\n"
            f"Хотите изменить? Напишите: изменить",
            parse_mode="Markdown"
        )
        return
    
    await message.answer(
        "Добро пожаловать! 👋\n\n"
        "Для регистрации напишите ваше **ФИО** как в 1С.\n\n"
        "Например: `Иванов Иван Иванович`",
        parse_mode="Markdown"
    )
    await state.set_state(UserRegistration.waiting_for_fio)


@dp.callback_query(F.data.startswith("select:"))
async def handle_manager_selection(callback: types.CallbackQuery, state: FSMContext):
    """Handle manager selection from inline keyboard"""
    selected_fio = callback.data.replace("select:", "")
    user_id = str(callback.from_user.id)
    
    # Find full FIO if truncated
    full_fio = selected_fio
    for manager in MANAGERS_LIST:
        if manager.startswith(selected_fio) or selected_fio in manager:
            full_fio = manager
            break
    
    # Normalize
    fio_normalized = normalize_fio(full_fio)
    
    # Save user
    users = load_users()
    users[user_id] = {
        "user_id": user_id,
        "fio": fio_normalized
    }
    save_users(users)
    
    # Clear state
    await state.clear()
    
    # Update message
    await callback.message.edit_text(
        f"✅ Регистрация завершена!\n\n"
        f"Ваше ФИО: **{fio_normalized}**\n"
        f"Telegram ID: `{user_id}`\n\n"
        f"Теперь вы будете получать уведомления о проблемах с доставкой.",
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def handle_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Handle cancel button"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Регистрация отменена.\n\n"
        "Чтобы начать заново, отправьте /start"
    )
    await callback.answer()


@dp.message(F.text)
async def handle_text(message: types.Message, state: FSMContext):
    """Handle text messages (FIO input or commands)"""
    user_id = str(message.from_user.id)
    text = message.text.strip()
    
    # Check for "изменить" command
    if text.lower() == "изменить":
        users = load_users()
        if user_id in users:
            await message.answer(
                "Введите новое ФИО:",
                parse_mode="Markdown"
            )
            await state.set_state(UserRegistration.waiting_for_fio)
        else:
            await message.answer("Вы ещё не зарегистрированы. Отправьте /start")
        return
    
    # Check if waiting for FIO
    current_state = await state.get_state()
    if current_state != UserRegistration.waiting_for_fio:
        await message.answer(
            "Отправьте /start для регистрации или /help для справки."
        )
        return
    
    # Process FIO input
    input_fio = normalize_fio(text)
    
    # Check for exact match in managers list
    exact_match = None
    for manager in MANAGERS_LIST:
        if normalize_fio(manager).lower() == input_fio.lower():
            exact_match = manager
            break
    
    if exact_match:
        # Exact match - register immediately
        users = load_users()
        users[user_id] = {
            "user_id": user_id,
            "fio": normalize_fio(exact_match)
        }
        save_users(users)
        await state.clear()
        
        await message.answer(
            f"✅ Регистрация завершена!\n\n"
            f"Ваше ФИО: **{normalize_fio(exact_match)}**\n"
            f"Telegram ID: `{user_id}`\n\n"
            f"Теперь вы будете получать уведомления о проблемах с доставкой.",
            parse_mode="Markdown"
        )
        return
    
    # No exact match - find similar
    similar = find_similar_managers(input_fio, MANAGERS_LIST)
    
    if similar:
        # Found similar managers - offer choices
        keyboard = create_manager_keyboard(similar)
        
        await message.answer(
            f"🔍 ФИО **{input_fio}** не найдено в базе менеджеров.\n\n"
            f"Возможно, вы имели в виду:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    else:
        # No similar found - allow manual entry anyway
        await message.answer(
            f"❌ ФИО **{input_fio}** не найдено в базе менеджеров.\n\n"
            f"Проверьте правильность написания и попробуйте снова.\n\n"
            f"Или напишите ваше ФИО точно как в 1С.",
            parse_mode="Markdown"
        )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Handle /help command"""
    await message.answer(
        "📚 **Справка**\n\n"
        "Этот бот регистрирует менеджеров для получения уведомлений о проблемах с доставкой.\n\n"
        "**Команды:**\n"
        "/start - Регистрация\n"
        "/help - Справка\n\n"
        "**Как зарегистрироваться:**\n"
        "1. Отправьте /start\n"
        "2. Введите ваше ФИО как в 1С\n"
        "3. Выберите себя из списка (если нужно)\n\n"
        "Чтобы изменить ФИО, напишите: изменить",
        parse_mode="Markdown"
    )


async def main():
    """Start the bot"""
    global MANAGERS_LIST
    
    print("🤖 Manager Registration Bot starting...")
    print(f"📁 Users file: {USERS_FILE.absolute()}")
    print(f"📊 Excel file: {EXCEL_FILE.absolute()}")
    
    # Load managers from Excel
    MANAGERS_LIST = load_managers_from_excel()
    
    if not MANAGERS_LIST:
        print("⚠️ No managers loaded! Bot will still work but without suggestions.")
    
    # Start polling
    print("✅ Bot is running!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
