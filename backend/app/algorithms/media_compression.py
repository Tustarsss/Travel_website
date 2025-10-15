"""Compression utilities for diary media files."""

from __future__ import annotations

import zlib
from typing import Tuple


class MediaCompressionService:
    """Lossless compression service for binary media payloads."""

    COMPRESSION_LEVEL = 6
    MIN_COMPRESS_SIZE = 4096  # 4KB threshold to avoid tiny assets overhead
    MIN_COMPRESSION_RATIO = 0.95  # require at least 5% savings

    def compress(self, data: bytes) -> Tuple[bytes, bool, float]:
        """Compress binary data losslessly using zlib.

        Returns the compressed payload, whether compression was applied, and
        the resulting compressed/original size ratio.
        """
        original_size = len(data)
        if original_size == 0:
            return data, False, 1.0

        if original_size < self.MIN_COMPRESS_SIZE:
            return data, False, 1.0

        try:
            compressed = zlib.compress(data, self.COMPRESSION_LEVEL)
        except zlib.error as exc:  # pragma: no cover - defensive
            print(f"Media compression error: {exc}")
            return data, False, 1.0

        compressed_size = len(compressed)
        ratio = compressed_size / original_size if original_size else 1.0

        if ratio > self.MIN_COMPRESSION_RATIO:
            return data, False, 1.0

        return compressed, True, ratio

    def decompress(self, data: bytes, is_compressed: bool) -> bytes:
        """Restore binary data to its original form."""
        if not is_compressed:
            return data

        try:
            return zlib.decompress(data)
        except zlib.error as exc:  # pragma: no cover - defensive
            raise ValueError(f"Failed to decompress media payload: {exc}") from exc


media_compression_service = MediaCompressionService()
