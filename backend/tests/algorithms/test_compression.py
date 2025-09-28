from __future__ import annotations

import pytest

from app.algorithms import compress_text, decompress_text


def test_round_trip_restores_original_text() -> None:
    original = "杭州西湖美景令人流连忘返" * 10
    compressed = compress_text(original)
    restored = decompress_text(compressed)
    assert restored == original


def test_compression_reduces_size_by_half_for_repetitive_text() -> None:
    original = ("scenic spot data " * 1000).strip()
    compressed = compress_text(original, level=9)
    ratio = len(compressed) / len(original.encode("utf-8"))
    assert ratio <= 0.5


def test_invalid_compression_level_raises_value_error() -> None:
    with pytest.raises(ValueError):
        compress_text("test", level=15)


def test_decompress_invalid_payload_raises_error() -> None:
    with pytest.raises(Exception):
        decompress_text(b"not a valid zlib payload")
