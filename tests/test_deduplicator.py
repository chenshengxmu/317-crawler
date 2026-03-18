"""
Unit tests for deduplication module.
"""

import pytest
from processing.deduplicator import Deduplicator


class TestDeduplicator:
    """Test Deduplicator class."""

    def test_normalize_url(self):
        """Test URL normalization."""
        url1 = "https://example.com/article?utm_source=test&id=123"
        url2 = "https://example.com/article?id=123"

        normalized1 = Deduplicator.normalize_url(url1)
        normalized2 = Deduplicator.normalize_url(url2)

        # Should remove tracking parameters
        assert 'utm_source' not in normalized1
        assert 'id=123' in normalized1
        assert normalized1 == normalized2

    def test_generate_url_hash(self):
        """Test URL hash generation."""
        url = "https://example.com/article"
        hash1 = Deduplicator.generate_url_hash(url)
        hash2 = Deduplicator.generate_url_hash(url)

        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hash length

    def test_generate_content_hash(self):
        """Test content hash generation."""
        content = "这是测试内容"
        hash1 = Deduplicator.generate_content_hash(content)
        hash2 = Deduplicator.generate_content_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 32

        # Different content should produce different hash
        content2 = "这是不同的内容"
        hash3 = Deduplicator.generate_content_hash(content2)
        assert hash1 != hash3

    def test_calculate_similarity(self):
        """Test similarity calculation."""
        text1 = "这是一段测试文本"
        text2 = "这是一段测试文本"
        text3 = "完全不同的文本"

        sim1 = Deduplicator.calculate_similarity(text1, text2)
        sim2 = Deduplicator.calculate_similarity(text1, text3)

        assert sim1 == 1.0  # Identical texts
        assert sim2 < sim1  # Different texts have lower similarity
