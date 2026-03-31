"""
Excel parser service.

Parses Excel file and extracts rows with triggers.
Handles FIO normalization and generates unique row hashes.
"""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

import config
from database.models import User

logger = logging.getLogger(__name__)


@dataclass
class TriggerRow:
    """
    Represents a row with a trigger (problem detected).
    
    Attributes:
        row_index: Original row index in Excel
        order_info: Order identification (first column)
        manager_fio: Manager's full name from column 10
        manager_fio_normalized: Normalized FIO (ё -> е)
        trigger_type: 1 for "problem 1", 2 for "problem 2"
        trigger_value: Actual value in trigger column
        row_hash: Unique hash for deduplication
    """
    row_index: int
    order_info: str
    manager_fio: str
    manager_fio_normalized: str
    trigger_type: int  # 1 or 2
    trigger_value: str
    row_hash: str


def generate_row_hash(order_info: str, manager_fio: str, trigger_type: int) -> str:
    """
    Generate unique hash for a row.
    
    The hash is based on:
    - Order information (first column)
    - Manager FIO
    - Trigger type (1 or 2)
    
    This ensures we don't send duplicate notifications for the same
    order + manager + problem type combination.
    
    Args:
        order_info: Order identification string
        manager_fio: Manager's full name
        trigger_type: 1 or 2
        
    Returns:
        MD5 hash string
    """
    # Normalize manager FIO for consistent hashing
    fio_normalized = User.normalize_fio(manager_fio)
    
    # Create hash from combined string
    combined = f"{order_info}|{fio_normalized}|{trigger_type}"
    return hashlib.md5(combined.encode()).hexdigest()


def parse_excel_file(filepath: Path) -> list[TriggerRow]:
    """
    Parse Excel file and extract rows with triggers.
    
    Args:
        filepath: Path to Excel file
        
    Returns:
        List of TriggerRow objects for rows with triggers
        
    How it works:
    1. Read Excel file with pandas
    2. Skip header rows (use DATA_START_ROW from config)
    3. For each data row:
       a. Check if trigger column 1 (second to last) has value
       b. Check if trigger column 2 (last) has value
       c. If trigger found, extract manager FIO and create TriggerRow
    4. Return list of found triggers
    """
    logger.info(f"Parsing Excel file: {filepath}")
    
    triggers: list[TriggerRow] = []
    
    try:
        # Read Excel file
        df = pd.read_excel(filepath, engine="openpyxl")
        
        logger.info(f"File loaded: {len(df)} rows, {len(df.columns)} columns")
        
        # Get column count for accessing last columns
        num_columns = len(df.columns)
        
        if num_columns < 12:
            logger.warning(f"Unexpected column count: {num_columns}. Expected 12.")
        
        # Iterate over data rows (skip headers)
        for idx in range(config.DATA_START_ROW, len(df)):
            row = df.iloc[idx]
            
            # Get order info (first column)
            order_info = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
            
            # Skip rows without order info (empty rows, section headers, etc.)
            if not order_info or order_info == "nan":
                continue
            
            # Skip rows that look like headers/sections
            if "Задание на перевозку" in order_info and "Заказ" not in order_info:
                continue
            
            # Get manager FIO (column 10, index 9)
            manager_fio = str(row.iloc[config.MANAGER_COLUMN_INDEX]) if pd.notna(row.iloc[config.MANAGER_COLUMN_INDEX]) else ""
            
            # Skip if no manager
            if not manager_fio or manager_fio == "nan":
                continue
            
            # Normalize manager FIO
            manager_fio_normalized = User.normalize_fio(manager_fio)
            
            # Check trigger columns
            # RULE: If BOTH columns have values, send only trigger 1 (priority)
            trigger_1_value = row.iloc[config.TRIGGER_1_COLUMN_INDEX]
            trigger_2_value = row.iloc[config.TRIGGER_2_COLUMN_INDEX]
            
            has_trigger_1 = (pd.notna(trigger_1_value) and 
                           str(trigger_1_value).strip() and 
                           str(trigger_1_value).strip() != "Наименование проблемы 1")
            
            has_trigger_2 = (pd.notna(trigger_2_value) and 
                           str(trigger_2_value).strip() and 
                           str(trigger_2_value).strip() != "Наименование проблемы 2")
            
            # If trigger 1 exists (regardless of trigger 2), use trigger 1
            if has_trigger_1:
                trigger_1_str = str(trigger_1_value).strip()
                row_hash = generate_row_hash(order_info, manager_fio, 1)
                
                triggers.append(TriggerRow(
                    row_index=idx,
                    order_info=order_info,
                    manager_fio=manager_fio,
                    manager_fio_normalized=manager_fio_normalized,
                    trigger_type=1,
                    trigger_value=trigger_1_str,
                    row_hash=row_hash
                ))
                
                logger.debug(
                    f"Trigger 1 found: row {idx}, "
                    f"manager={manager_fio}, value={trigger_1_str}"
                )
            
            # Only use trigger 2 if trigger 1 is NOT present
            elif has_trigger_2:
                trigger_2_str = str(trigger_2_value).strip()
                row_hash = generate_row_hash(order_info, manager_fio, 2)
                
                triggers.append(TriggerRow(
                    row_index=idx,
                    order_info=order_info,
                    manager_fio=manager_fio,
                    manager_fio_normalized=manager_fio_normalized,
                    trigger_type=2,
                    trigger_value=trigger_2_str,
                    row_hash=row_hash
                ))
                
                logger.debug(
                    f"Trigger 2 found: row {idx}, "
                    f"manager={manager_fio}, value={trigger_2_str}"
                )
        
        logger.info(f"Parsing complete: found {len(triggers)} triggers")
        return triggers
        
    except Exception as e:
        logger.error(f"Error parsing Excel file: {e}")
        raise


def get_test_triggers() -> list[TriggerRow]:
    """
    Generate test triggers for development.
    
    Returns:
        List of fake TriggerRow objects for testing
    """
    return [
        TriggerRow(
            row_index=10,
            order_info="Заказ клиента ",
            manager_fio="Имя Фамилия Отчество",
            manager_fio_normalized="Имя Фамилия Отчество",
            trigger_type=1,
            trigger_value="Тест проблема 1",
            row_hash="test_hash_001"
        ),
        TriggerRow(
            row_index=15,
            order_info="Заказ клиента ",
            manager_fio="Имя Фамилия Отчество",
            manager_fio_normalized="Имя Фамилия Отчество",
            trigger_type=2,
            trigger_value="Тест проблема 2",
            row_hash="test_hash_002"
        ),
    ]

