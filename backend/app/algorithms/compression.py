"""Utility helpers for lossless text compression."""

from __future__ import annotations

import zlib
from typing import Final

_ENCODING: Final[str] = "utf-8"


def compress_text(text: str, *, level: int = 9) -> bytes:
    """Compress UTF-8 text using zlib.

    Parameters
    ----------
    text:
        Source text to compress. The function encodes the string as UTF-8 before
        compression.
    level:
        Compression level (0-9). Defaults to the maximum compression.
    """

    if not 0 <= level <= 9:
        raise ValueError("level must be between 0 and 9")
    data = text.encode(_ENCODING)
    return zlib.compress(data, level)


def decompress_text(data: bytes) -> str:
    """Decompress UTF-8 text previously produced by :func:`compress_text`."""

    return zlib.decompress(data).decode(_ENCODING)
