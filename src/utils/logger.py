"""Centralized structured logging."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def setup_logger(level: str = "INFO") -> None:
    """Configure loguru for both console and rotating file output."""
    logger.remove()

    # Console – human readable
    logger.add(
        sys.stderr,
        level=level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True,
    )

    # File – structured / JSON-friendly
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger.add(
        log_dir / "bot_{time:YYYY-MM-DD}.log",
        level=level.upper(),
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    logger.info("Logger initialized | level={}", level.upper())
