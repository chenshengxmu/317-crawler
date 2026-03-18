"""
Logging configuration using Loguru.
Provides structured logging with rotation and retention.
"""

import sys
from pathlib import Path
from loguru import logger

from config import settings


def setup_logger(log_file: str = "app.log", module_name: str = None):
    """
    Setup logger with file rotation and console output.

    Args:
        log_file: Log file name
        module_name: Module name for filtering (optional)
    """
    # Remove default handler
    logger.remove()

    # Console handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )

    # File handler with rotation
    log_path = Path("logs") / log_file
    log_path.parent.mkdir(exist_ok=True)

    logger.add(
        str(log_path),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="zip",
        encoding="utf-8",
    )

    return logger


# Setup default logger
setup_logger()
