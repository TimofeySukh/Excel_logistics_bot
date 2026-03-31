"""
Database module for Delivery Monitoring Bot.

Provides async SQLite database operations:
- Initialize database schema
- CRUD operations for Users and ProcessedRows
"""

import aiosqlite
import logging
from pathlib import Path
from typing import Optional

from database.models import User, ProcessedRow
import config

logger = logging.getLogger(__name__)


async def init_database() -> None:
    """
    Initialize the database schema.
    
    Creates tables if they don't exist:
    - users: Telegram ID <-> FIO mapping
    - processed_rows: Tracking processed Excel rows
    """
    # Ensure database directory exists
    config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Create users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                fio TEXT NOT NULL,
                fio_normalized TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for fast FIO lookup
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_fio_normalized 
            ON users(fio_normalized)
        """)
        
        # Create processed_rows table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS processed_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                row_hash TEXT UNIQUE NOT NULL,
                trigger_type INTEGER NOT NULL,
                order_info TEXT,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.commit()
        logger.info(f"Database initialized at {config.DATABASE_PATH}")


# =============================================================================
# USER OPERATIONS
# =============================================================================

async def add_user(telegram_id: int, fio: str) -> User:
    """
    Add a new user or update existing one.
    
    Args:
        telegram_id: User's Telegram ID
        fio: User's full name (FIO)
        
    Returns:
        Created/updated User object
    """
    fio_normalized = User.normalize_fio(fio)
    
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Use INSERT OR REPLACE to handle both new and existing users
        await db.execute("""
            INSERT OR REPLACE INTO users (telegram_id, fio, fio_normalized)
            VALUES (?, ?, ?)
        """, (telegram_id, fio, fio_normalized))
        await db.commit()
        
        logger.info(f"User registered: {telegram_id} -> {fio}")
        return User(telegram_id=telegram_id, fio=fio, fio_normalized=fio_normalized)


async def get_user_by_fio(fio: str) -> Optional[User]:
    """
    Find user by FIO (with normalization).
    
    Args:
        fio: Full name to search for
        
    Returns:
        User object if found, None otherwise
    """
    fio_normalized = User.normalize_fio(fio)
    
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, telegram_id, fio, fio_normalized, created_at
            FROM users
            WHERE fio_normalized = ?
        """, (fio_normalized,)) as cursor:
            row = await cursor.fetchone()
            
            if row:
                return User(
                    id=row["id"],
                    telegram_id=row["telegram_id"],
                    fio=row["fio"],
                    fio_normalized=row["fio_normalized"],
                    created_at=row["created_at"]
                )
            return None


async def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    """
    Find user by Telegram ID.
    
    Args:
        telegram_id: Telegram user ID
        
    Returns:
        User object if found, None otherwise
    """
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, telegram_id, fio, fio_normalized, created_at
            FROM users
            WHERE telegram_id = ?
        """, (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            
            if row:
                return User(
                    id=row["id"],
                    telegram_id=row["telegram_id"],
                    fio=row["fio"],
                    fio_normalized=row["fio_normalized"],
                    created_at=row["created_at"]
                )
            return None


async def get_all_users() -> list[User]:
    """
    Get all registered users.
    
    Returns:
        List of all User objects
    """
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, telegram_id, fio, fio_normalized, created_at
            FROM users
        """) as cursor:
            rows = await cursor.fetchall()
            
            return [
                User(
                    id=row["id"],
                    telegram_id=row["telegram_id"],
                    fio=row["fio"],
                    fio_normalized=row["fio_normalized"],
                    created_at=row["created_at"]
                )
                for row in rows
            ]


# =============================================================================
# PROCESSED ROWS OPERATIONS
# =============================================================================

async def is_row_processed(row_hash: str) -> bool:
    """
    Check if a row has already been processed.
    
    Args:
        row_hash: Unique hash of the row
        
    Returns:
        True if already processed, False otherwise
    """
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute("""
            SELECT 1 FROM processed_rows WHERE row_hash = ?
        """, (row_hash,)) as cursor:
            return await cursor.fetchone() is not None


async def mark_row_processed(row_hash: str, trigger_type: int, order_info: str = None) -> None:
    """
    Mark a row as processed.
    
    Args:
        row_hash: Unique hash of the row
        trigger_type: 1 or 2 (which trigger column)
        order_info: Optional order information for logging
    """
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        try:
            await db.execute("""
                INSERT INTO processed_rows (row_hash, trigger_type, order_info)
                VALUES (?, ?, ?)
            """, (row_hash, trigger_type, order_info))
            await db.commit()
            logger.debug(f"Row marked as processed: {row_hash}")
        except aiosqlite.IntegrityError:
            # Already processed (race condition protection)
            logger.debug(f"Row already processed: {row_hash}")


async def get_processed_rows_count() -> int:
    """
    Get count of processed rows.
    
    Returns:
        Number of processed rows
    """
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM processed_rows") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

