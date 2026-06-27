"""Structured logging to console + file (audit trail for compliance)."""
import logging
import os
from logging.handlers import RotatingFileHandler

os.makedirs("logs", exist_ok=True)

_FMT = "%(asctime)s | %(levelname)-7s | %(name)-12s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_FMT))
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        "logs/trading_bot.log", maxBytes=5_000_000, backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(_FMT))
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger
