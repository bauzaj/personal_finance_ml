"""
Centralized logging configuration.

Configures structured logging for the entire application. Use get_logger(__name__)
in each module to get a properly configured logger.

Important: never log access tokens, private keys, or personal financial data.
"""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Get a logger configured with consistent formatting and INFO level."""
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if get_logger is called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

    return logger
