import logging
import sys

import coloredlogs

from src.core.config import LOGGER_LEVEL


def setup_logging(verbose: bool = False) -> None:
    log_level = "DEBUG" if verbose else LOGGER_LEVEL.upper()

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.disabled = False

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    coloredlogs.install(
        level=log_level,
        logger=root_logger,
        fmt=log_format,
        datefmt=date_format,
        stream=sys.stdout,
        isatty=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
