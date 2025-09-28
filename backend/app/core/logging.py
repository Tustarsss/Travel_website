"""Logging configuration helpers."""

import logging

_LOGGING_CONFIGURED = False


def configure_logging(level: int | None = None) -> None:
    """Configure the root logger once."""

    global _LOGGING_CONFIGURED

    if _LOGGING_CONFIGURED:
        return

    logging.basicConfig(
        level=level or logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    _LOGGING_CONFIGURED = True
