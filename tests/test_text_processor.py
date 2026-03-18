"""
Unit tests for text processing module.
"""

import pytest
from processing.text_processor import TextProcessor


class TestTextProcessor:
    """Test TextProcessor class."""

    def test_clean_html(self):
        """Test HTML cleaning."""
        html = '<p>这是一段<strong>测试</strong>文本</p><script>alert("test")</script>'
        result = TextProcessor.clean_html(html)
        assert '<' not in result
        assert '测试' in result
        assert 'script' not in result.lower()

    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        text = "这是   一段\n\n\n测试   文本"
        result = TextProcessor.normalize_whitespace(text)
        assert '   ' not in result
        assert '\n\n\n' not in result

    def test_clean_article_text(self):
        """Test full article cleaning."""
        html = '<p>这是测试文章</p><script>bad</script>  http://example.com  '
        result = TextProcessor.clean_article_text(html, remove_urls_flag=True)
        assert 'script' not in result
        assert 'http' not in result
        assert '这是测试文章' in result

    def test_extract_summary(self):
        """Test summary extraction."""
        text = "这是一篇很长的文章。" * 50
        summary = TextProcessor.extract_summary(text, max_length=100)
        assert len(summary) <= 120  # Allow some margin
        assert '这是一篇' in summary

    def test_is_valid_article(self):
        """Test article validation."""
        short_text = "太短"
        long_text = "这是一篇足够长的文章。" * 10

        assert not TextProcessor.is_valid_article(short_text, min_length=50)
        assert TextProcessor.is_valid_article(long_text, min_length=50)

    def test_handle_encoding(self):
        """Test encoding handling."""
        # UTF-8 string
        text = "中文测试"
        result = TextProcessor.handle_encoding(text)
        assert result == text

        # Bytes
        text_bytes = "中文测试".encode('utf-8')
        result = TextProcessor.handle_encoding(text_bytes)
        assert result == "中文测试"
