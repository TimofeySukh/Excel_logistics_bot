"""
Configuration module for Delivery Monitoring Bot.

Loads settings from environment variables (.env file).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# BOT CONFIGURATION
# =============================================================================

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file!")

# =============================================================================
# EXCEL FILE CONFIGURATION
# =============================================================================

# URL to download Excel file (change for production)
# Note: spaces and special chars are URL-encoded:
#   %20 = space, %28 = (, %29 = )
EXCEL_FILE_URL: str = os.getenv(
    "EXCEL_FILE_URL",
    ""
)

# =============================================================================
# ⏰ INTERVAL CONFIGURATION - EASY TO CHANGE!
# =============================================================================
# How often to check Excel file for new problems (in minutes)
# Change this value to adjust check frequency:
#   1 = every minute (for testing)
#   5 = every 5 minutes (for production)
CHECK_INTERVAL_MINUTES: int = 5

# Temporary directory for downloaded files
TEMP_DIR: Path = Path(__file__).parent / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# =============================================================================
# USERS FILE - WHERE REGISTERED MANAGERS ARE STORED
# =============================================================================
# Path to users.json from registration bot (contains FIO <-> Telegram ID mapping)
USERS_JSON_PATH: Path = Path(__file__).parent / "registration_bot" / "users.json"

# =============================================================================
# EXCEL PARSING CONFIGURATION
# =============================================================================

# Row index where actual data starts (0-based, after headers)
DATA_START_ROW: int = 6

# Column indices (0-based)
MANAGER_COLUMN_INDEX: int = 9  # Column 10 - "Менеджер" (Manager)
TRIGGER_1_COLUMN_INDEX: int = -2  # Second to last - "Наименование проблемы 1"
TRIGGER_2_COLUMN_INDEX: int = -1  # Last column - "Наименование проблемы 2"

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

DATABASE_PATH: Path = Path(__file__).parent / "database" / "bot.db"

# =============================================================================
# NOTIFICATION MESSAGES
# =============================================================================

# Message for trigger 1 (second to last column) - No document rework needed
MESSAGE_TRIGGER_1: str = (
    "⚠️ Заказ сегодня не будет доставлен.\n\n"
    "Переделка документов не требуется.\n"
    "Доставка будет осуществлена в ближайшую дату согласно графику доставок."
)

# Message for trigger 2 (last column) - Document rework required
MESSAGE_TRIGGER_2: str = (
    "🔴 Заказ сегодня не будет доставлен.\n\n"
    "⚠️ Требуется переделка документов на ближайшую дату "
    "согласно графику доставок."
)

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

