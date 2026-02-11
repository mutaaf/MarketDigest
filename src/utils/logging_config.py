"""Logging configuration for the market digest system."""

import logging
import sys
from pathlib import Path

from config.settings import get_settings


def setup_logging(name: str = "market_digest") -> logging.Logger:
    settings = get_settings()
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # File handler
    log_dir = settings.logs_dir
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "market_digest.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(module_name: str) -> logging.Logger:
    return logging.getLogger(f"market_digest.{module_name}")
