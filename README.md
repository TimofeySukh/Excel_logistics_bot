# Delivery Monitoring Bot

**Automated Telegram notification system for logistics operations**

> ⚠️ **Proprietary Software** - All Rights Reserved  
> This project is developed for a Russian logistics company and is **NOT** available for public use, modification, or distribution.

## Overview

An intelligent Telegram bot system that automates delivery problem notifications for logistics managers. The system monitors Excel reports, detects delivery issues, and sends targeted notifications to responsible managers via Telegram.

**Tech Stack:** Python, aiogram (Telegram Bot API), pandas, APScheduler, SQLite

**Key Features:**
- 🔄 Automated Excel report parsing every 5 minutes
- 🎯 Smart FIO (Full Name) matching with fuzzy search
- 🔔 Targeted notifications to responsible managers only
- 🗄️ SQLite-based deduplication system
- 🌐 Cyrillic character normalization (ё ↔ е)
- 👥 Two-bot architecture: notification delivery + user registration

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Main Notification Bot                    │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Scheduler   │───▶│ Excel Parser │───▶│ Notification │  │
│  │  (5 min)     │    │              │    │   Sender     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Download   │    │ Trigger      │    │   Database   │  │
│  │   Manager    │    │ Detection    │    │ (SQLite)     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ FIO Lookup
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Registration Bot                           │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ FIO Input    │───▶│ Fuzzy Match  │───▶│  User Store  │  │
│  │   Handler    │    │   Engine     │    │  (JSON)      │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Scheduler** downloads Excel file from URL every 5 minutes
2. **Excel Parser** identifies rows with delivery problems (trigger columns)
3. **FIO Matcher** extracts manager's full name and normalizes Cyrillic characters
4. **User Lookup** finds Telegram ID from registration database
5. **Notification Sender** delivers personalized message to manager
6. **Database** prevents duplicate notifications via row hashing

## Project Structure

### Root Directory

```
delivery-monitoring-bot/
├── main.py                 # Entry point for notification bot
├── config.py               # Centralized configuration management
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (gitignored)
├── .env.example            # Template for environment configuration
├── .gitignore              # Git ignore rules
├── SOW_version_2.md        # Technical specification (Russian)
└── README.md               # This file
```

#### **main.py**
Main application entry point. Initializes the bot, sets up the scheduler, handles graceful shutdown with SIGINT/SIGTERM signals, and manages the async event loop.

#### **config.py**
Centralized configuration module. Loads settings from environment variables, defines Excel column mappings, notification message templates, and configurable check intervals. Implements Path-based file management for cross-platform compatibility.

#### **requirements.txt**
Python package dependencies:
- `aiogram` - Modern Telegram Bot framework
- `pandas` - Excel file parsing
- `openpyxl` - Excel file engine
- `python-dotenv` - Environment variable management
- `aiohttp` - Async HTTP client for downloads
- `apscheduler` - Task scheduling

### `/bot/` - Telegram Bot Handlers

```
bot/
├── __init__.py
├── handlers.py             # Command handlers (/start, /help)
└── notifications.py        # Notification delivery logic
```

#### **handlers.py**
Telegram command handlers. Implements `/start` (welcome message), `/help` (usage guide), and admin-only `/check` command. Uses aiogram Router pattern for handler organization.

#### **notifications.py**
Core notification engine. Loads user database from JSON, performs FIO-to-Telegram ID mapping with Cyrillic normalization, sends notifications with retry logic, and updates processed row database to prevent duplicates.

### `/database/` - Data Persistence Layer

```
database/
├── __init__.py
├── models.py               # Data models (User, ProcessedRow)
└── db.py                   # Database operations (aiosqlite)
```

#### **models.py**
Dataclass models for type-safe database operations:
- `User`: Telegram ID ↔ FIO mapping with normalization
- `ProcessedRow`: Deduplication tracking via MD5 hashing

#### **db.py**
Async SQLite database manager using `aiosqlite`. Implements CRUD operations for users and processed rows, automatic schema creation, and connection pooling.

### `/services/` - Business Logic Layer

```
services/
├── __init__.py
├── excel_downloader.py     # File download manager
├── excel_parser.py         # Excel parsing engine
└── scheduler.py            # APScheduler configuration
```

#### **excel_downloader.py**
Async file downloader using `aiohttp`. Downloads Excel files from URLs, manages temporary file storage, implements cleanup strategies (keep last N files), and handles network errors with custom exceptions.

#### **excel_parser.py**
Excel parsing engine using `pandas`. Reads Excel files, identifies trigger columns (problem indicators), extracts manager FIO from configured column, generates unique row hashes (MD5) for deduplication, and returns structured `TriggerRow` objects.

#### **scheduler.py**
APScheduler integration. Configures AsyncIOScheduler with interval triggers, orchestrates the full check pipeline (download → parse → notify → cleanup), implements error handling and logging for scheduled tasks.

### `/registration_bot/` - User Registration System

```
registration_bot/
├── main.py                 # Standalone registration bot
├── users.json              # User database (gitignored)
├── requirements.txt        # Registration bot dependencies
├── .env                    # Registration bot token (gitignored)
└── .env.example            # Template configuration
```

#### **main.py** (Registration Bot)
Standalone bot for user registration. Implements FSM (Finite State Machine) for registration flow, fuzzy FIO matching with partial name search, inline keyboard suggestions for similar names, Excel-based manager list validation, and JSON persistence for user data.

**Features:**
- Interactive FIO input with suggestions
- Handles typos with fuzzy matching (surname/name/patronymic parts)
- Validates against manager list from Excel
- Cyrillic normalization (ё → е) for consistent matching
- InlineKeyboard for easy selection from similar names

### `/temp/` - Temporary File Storage

```
temp/
└── (downloaded Excel files)
```

Temporary storage for downloaded Excel reports. Automatically cleaned up by the scheduler (keeps last 3 files). **Gitignored** to prevent large files in repository.

### `/test_env/` - Development Testing

```
test_env/
└── (test Excel files)
```

Development environment for testing Excel parsing logic. Contains sample Excel files with test data. **Gitignored** to protect sensitive data.

## Technical Highlights

### 1. Cyrillic Character Normalization
Russian names can be written with 'ё' or 'е' inconsistently. The system normalizes all FIO strings by replacing 'ё' → 'е' for reliable matching.

```python
def normalize_fio(fio: str) -> str:
    return fio.replace("ё", "е").replace("Ё", "Е").strip()
```

### 2. Row Deduplication System
Prevents duplicate notifications using MD5 hashing of:
- Order identification
- Manager FIO (normalized)
- Trigger type (1 or 2)

```python
def generate_row_hash(order_info: str, manager_fio: str, trigger_type: int) -> str:
    fio_normalized = User.normalize_fio(manager_fio)
    combined = f"{order_info}|{fio_normalized}|{trigger_type}"
    return hashlib.md5(combined.encode()).hexdigest()
```

### 3. Fuzzy FIO Matching
Registration bot implements intelligent name matching by splitting FIO into parts (surname, name, patronymic) and matching partial strings.

```python
def find_similar_managers(input_fio: str, managers: list[str]) -> list[str]:
    input_parts = normalize_fio(input_fio).lower().split()
    # Matches any manager whose FIO contains all input parts
    return [m for m in managers if all(part in m.lower() for part in input_parts)]
```

### 4. Two-Trigger System
Different notification messages for two types of delivery problems:

- **Trigger 1** (Column -2): Delivery delayed, no document changes needed
- **Trigger 2** (Column -1): Delivery delayed, documents must be updated

### 5. Async-First Architecture
Uses `asyncio` throughout for non-blocking I/O:
- `aiohttp` for HTTP downloads
- `aiosqlite` for database operations  
- `aiogram` for Telegram API
- APScheduler's `AsyncIOScheduler` for task scheduling

### 6. Graceful Shutdown
Handles SIGINT/SIGTERM signals for clean shutdown:
```python
signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)
```

### 7. Configurable Check Interval
Single configuration point for adjustment:
```python
CHECK_INTERVAL_MINUTES: int = 5  # Easy to change
```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    fio TEXT NOT NULL,
    fio_normalized TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Processed Rows Table
```sql
CREATE TABLE processed_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    row_hash TEXT UNIQUE NOT NULL,
    trigger_type INTEGER NOT NULL,
    order_info TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Excel File Structure

Expected columns:
- **Column 1**: Order identification
- **Column 10**: Manager FIO (Full Name)
- **Column -2**: Trigger 1 (delivery problem without document changes)
- **Column -1**: Trigger 2 (delivery problem with document changes)

Data starts from row 7 (index 6) after headers.

## Environment Variables

### Main Bot (`.env`)
```env
BOT_TOKEN=<telegram_bot_token>
EXCEL_FILE_URL=<url_to_excel_report>
LOG_LEVEL=INFO
```

### Registration Bot (`registration_bot/.env`)
```env
BOT_TOKEN=<registration_bot_token>
```

## Development Decisions

### Why Two Separate Bots?
- **Separation of concerns**: Notification delivery vs user management
- **Security**: Registration bot can be restricted to admin/HR use
- **Scalability**: Independent deployment and scaling
- **Maintainability**: Isolated codebases for different functionalities

### Why JSON for User Storage?
- Simple read/write operations
- Easy manual editing if needed
- Shared between registration bot and main bot
- Low complexity for small user base (<1000 users)

### Why SQLite for Deduplication?
- ACID compliance for race condition prevention
- Fast lookups with indexed hash column
- Persistent storage across restarts
- Automatic cleanup of old entries possible

### Why APScheduler?
- Async support with `AsyncIOScheduler`
- Simple interval-based triggers
- No external dependencies (no Redis/Celery needed)
- Runs in the same process as the bot

## Message Localization

All user-facing messages are in Russian (target audience):
- Команды: `/start`, `/help`
- Уведомления о проблемах доставки
- Инструкции по регистрации
- Сообщения об ошибках

## Error Handling

- **Network errors**: Retry with exponential backoff
- **Excel parsing errors**: Logged, skip current check
- **Database errors**: Logged, continue operation
- **Telegram API errors**: Logged per notification, continue batch
- **Missing user**: Logged with manager FIO for manual registration

## Logging Strategy

Structured logging with timestamps:
- `INFO`: Normal operations (checks, notifications sent)
- `WARNING`: Missing users, retries
- `ERROR`: Failed downloads, parsing errors
- `DEBUG`: Detailed flow information (disabled in production)

## Security Considerations

### Gitignored Files
- `.env` - Bot tokens and API keys
- `users.json` - Personal data (Telegram IDs + FIO)
- `*.db` - Database with processed rows
- `temp/` - Downloaded Excel files may contain sensitive data
- `test_env/` - Test files with real data

### Access Control
- Admin IDs hardcoded in `bot/handlers.py` for manual checks
- Registration bot should be access-controlled
- Excel URL should use HTTPS with authentication

## Performance Metrics

- **Check interval**: 5 minutes (configurable)
- **Excel parsing**: ~1-2 seconds for 1000 rows
- **Notification delivery**: ~0.5 seconds per message
- **Database queries**: <10ms per lookup
- **Memory footprint**: ~50MB base + Excel file size

## Future Enhancements

- Web dashboard for user management
- Real-time WebSocket updates instead of polling
- PostgreSQL for larger user base
- Multi-language support
- Notification delivery confirmation tracking
- Analytics dashboard for delivery problems

## License

**All Rights Reserved** © 2025

This software is proprietary and confidential. Unauthorized copying, modification, distribution, or use of this software, via any medium, is strictly prohibited without explicit written permission from the owner.

This project is intended as a **portfolio demonstration** only.

---

**Project Status**: Production-ready for Russian logistics company  
**Language**: Python 3.11+  
**Framework**: aiogram 3.x  
**Author**: Portfolio Project
