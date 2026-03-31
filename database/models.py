"""
Database models for Delivery Monitoring Bot.

Contains dataclasses representing database entities:
- User: mapping between Telegram ID and FIO (full name)
- ProcessedRow: tracking already processed Excel rows to avoid duplicates
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """
    Represents a registered user.
    
    Attributes:
        id: Primary key in database
        telegram_id: User's Telegram ID (unique)
        fio: Original FIO as entered by user (e.g., "Иванов Иван Иванович")
        fio_normalized: FIO with 'ё' replaced by 'е' for matching
        created_at: Registration timestamp
    """
    telegram_id: int
    fio: str
    fio_normalized: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    @staticmethod
    def normalize_fio(fio: str) -> str:
        """
        Normalize FIO by replacing 'ё' with 'е' and stripping whitespace.
        
        This is needed because Excel might have different variations
        of the same name (Ёжик vs Ежик).
        
        Args:
            fio: Original FIO string
            
        Returns:
            Normalized FIO with 'ё' -> 'е' and stripped whitespace
        """
        return fio.replace("ё", "е").replace("Ё", "Е").strip()


@dataclass
class ProcessedRow:
    """
    Represents an already processed Excel row.
    
    Used to track which rows have been processed to avoid
    sending duplicate notifications.
    
    Attributes:
        id: Primary key in database
        row_hash: Unique hash of the row (order_id + manager + trigger_type)
        trigger_type: 1 for "problem 1" column, 2 for "problem 2" column
        order_info: Optional order information for logging
        processed_at: When this row was processed
    """
    row_hash: str
    trigger_type: int
    order_info: Optional[str] = None
    id: Optional[int] = None
    processed_at: Optional[datetime] = None

