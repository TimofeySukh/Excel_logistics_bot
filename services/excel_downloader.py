"""
Excel file downloader service.

Downloads Excel file from URL asynchronously.
Handles network errors and saves to temporary directory.
"""

import aiohttp
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

import config

logger = logging.getLogger(__name__)


class DownloadError(Exception):
    """Raised when file download fails."""
    pass


async def download_excel_file(url: str = None) -> Path:
    """
    Download Excel file from URL.
    
    Args:
        url: URL to download from. Defaults to config.EXCEL_FILE_URL
        
    Returns:
        Path to downloaded file
        
    Raises:
        DownloadError: If download fails
        
    How it works:
    1. Creates async HTTP session with aiohttp
    2. Sends GET request to URL
    3. Reads response content as bytes
    4. Saves to temp directory with timestamp
    5. Returns path to saved file
    """
    url = url or config.EXCEL_FILE_URL
    
    # Generate filename with timestamp to avoid conflicts
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"managers_problems_{timestamp}.xlsx"
    filepath = config.TEMP_DIR / filename
    
    logger.info(f"Downloading Excel file from: {url}")
    
    try:
        # Create timeout for the request (30 seconds)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                # Check if request was successful
                if response.status != 200:
                    raise DownloadError(
                        f"Failed to download file: HTTP {response.status}"
                    )
                
                # Read content
                content = await response.read()
                
                # Verify we got some data
                if not content:
                    raise DownloadError("Downloaded file is empty")
                
                # Save to file
                filepath.write_bytes(content)
                
                logger.info(
                    f"File downloaded successfully: {filepath} "
                    f"({len(content)} bytes)"
                )
                
                return filepath
                
    except aiohttp.ClientError as e:
        # Network-related errors (connection refused, timeout, etc.)
        raise DownloadError(f"Network error while downloading: {e}")
    except Exception as e:
        # Any other unexpected error
        raise DownloadError(f"Unexpected error while downloading: {e}")


def cleanup_temp_files(keep_last: int = 5) -> None:
    """
    Clean up old temporary files.
    
    Keeps only the last N files to prevent disk space issues.
    
    Args:
        keep_last: Number of recent files to keep
    """
    try:
        # Get all xlsx files in temp directory
        files = sorted(
            config.TEMP_DIR.glob("managers_problems_*.xlsx"),
            key=lambda f: f.stat().st_mtime,
            reverse=True  # Newest first
        )
        
        # Delete old files
        for old_file in files[keep_last:]:
            old_file.unlink()
            logger.debug(f"Deleted old temp file: {old_file}")
            
    except Exception as e:
        logger.warning(f"Error during temp file cleanup: {e}")


async def get_local_test_file() -> Optional[Path]:
    """
    Get path to local test file (for development).
    
    Returns:
        Path to test file if exists, None otherwise
    """
    test_file = Path(__file__).parent.parent / "test_env" / "ManagersProblems (XLSX).xlsx"
    
    if test_file.exists():
        logger.info(f"Using local test file: {test_file}")
        return test_file
    
    return None

