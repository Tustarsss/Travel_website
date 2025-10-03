"""Compression utilities for diary content."""

import zlib
from typing import Tuple


class DiaryCompressionService:
    """Service for compressing and decompressing diary content."""

    # Compression level: 0-9, where 6 is a good balance between speed and ratio
    COMPRESSION_LEVEL = 6
    
    # Minimum size threshold (bytes) - don't compress content smaller than this
    MIN_COMPRESS_SIZE = 1024  # 1KB
    
    # Compression ratio threshold - don't use compression if ratio > this value
    MIN_COMPRESSION_RATIO = 0.9  # Must achieve at least 10% reduction

    def compress_content(self, content: str) -> Tuple[bytes, bool, float]:
        """
        Compress diary content using zlib.
        
        Args:
            content: Original content string
            
        Returns:
            Tuple of (compressed_bytes, was_compressed, compression_ratio)
            - compressed_bytes: Compressed data (or original if not compressed)
            - was_compressed: Boolean indicating if compression was applied
            - compression_ratio: Ratio of compressed/original size
        """
        content_bytes = content.encode('utf-8')
        original_size = len(content_bytes)
        
        # Don't compress if too small
        if original_size < self.MIN_COMPRESS_SIZE:
            return content_bytes, False, 1.0
        
        try:
            compressed = zlib.compress(content_bytes, self.COMPRESSION_LEVEL)
            compressed_size = len(compressed)
            ratio = compressed_size / original_size
            
            # Check if compression is worth it
            if ratio > self.MIN_COMPRESSION_RATIO:
                return content_bytes, False, 1.0
            
            return compressed, True, ratio
            
        except zlib.error as e:
            # Compression failed, return original
            print(f"Compression error: {e}")
            return content_bytes, False, 1.0

    def decompress_content(self, compressed: bytes, is_compressed: bool) -> str:
        """
        Decompress diary content.
        
        Args:
            compressed: Compressed bytes (or original if not compressed)
            is_compressed: Boolean indicating if data is compressed
            
        Returns:
            Original content string
            
        Raises:
            ValueError: If decompression fails
        """
        if not is_compressed:
            # Data is not compressed, decode directly
            return compressed.decode('utf-8')
        
        try:
            decompressed = zlib.decompress(compressed)
            return decompressed.decode('utf-8')
        except zlib.error as e:
            raise ValueError(f"Decompression failed: {e}")
        except UnicodeDecodeError as e:
            raise ValueError(f"Decoding failed: {e}")

    def get_compression_stats(self, original_size: int, compressed_size: int) -> dict:
        """
        Calculate compression statistics.
        
        Args:
            original_size: Size of original content in bytes
            compressed_size: Size of compressed content in bytes
            
        Returns:
            Dictionary with compression statistics
        """
        ratio = compressed_size / original_size if original_size > 0 else 1.0
        saved_bytes = original_size - compressed_size
        saved_percent = (1 - ratio) * 100
        
        return {
            'original_size': original_size,
            'compressed_size': compressed_size,
            'ratio': ratio,
            'saved_bytes': saved_bytes,
            'saved_percent': saved_percent,
        }


# Singleton instance
compression_service = DiaryCompressionService()
