"""Logging configuration with datetime stamps."""

import logging
import sys


def setup_logging() -> None:
    """Configure logging with datetime format."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s   %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,  # Override any existing configuration
    )
