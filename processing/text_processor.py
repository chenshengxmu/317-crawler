"""
Text processing utilities for cleaning and normalizing Chinese content.
Handles HTML cleaning, encoding issues, and text extraction.
"""

import re
from typing import Optional
from bs4 import BeautifulSoup
import html


class TextProcessor:
    """Process and clean text content, especially for Chinese articles."""

    # Common Chinese punctuation normalization
    PUNCTUATION_MAP = {
        '，': ',',
        '。': '.',
        '！': '!',
        '？': '?',
        '；': ';',
        '：': ':',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '（': '(',
        '）': ')',
        '【': '[',
        '】': ']',
        '《': '<',
        '》': '>',
    }

    @staticmethod
    def clean_html(text: str) -> str:
        """
        Remove HTML tags and entities from text.

        Args:
            text: Raw HTML text

        Returns:
            Cleaned text without HTML
        """
        if not text:
            return ""

        # Parse HTML
        soup = BeautifulSoup(text, 'lxml')

        # Remove script and style tags
        for tag in soup(['script', 'style', 'iframe', 'noscript']):
            tag.decompose()

        # Get text
        text = soup.get_text()

        # Decode HTML entities
        text = html.unescape(text)

        return text

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """
        Normalize whitespace in text.

        Args:
            text: Input text

        Returns:
            Text with normalized whitespace
        """
        # Replace multiple spaces with single space
        text = re.sub(r'[ \t]+', ' ', text)

        # Replace multiple newlines with double newline
        text = re.sub(r'\n\s*\n+', '\n\n', text)

        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        return text.strip()

    @staticmethod
    def normalize_punctuation(text: str, to_english: bool = False) -> str:
        """
        Normalize Chinese punctuation.

        Args:
            text: Input text
            to_english: If True, convert to English punctuation

        Returns:
            Text with normalized punctuation
        """
        if not text:
            return ""

        if to_english:
            for cn_punct, en_punct in TextProcessor.PUNCTUATION_MAP.items():
                text = text.replace(cn_punct, en_punct)

        return text

    @staticmethod
    def remove_urls(text: str) -> str:
        """
        Remove URLs from text.

        Args:
            text: Input text

        Returns:
            Text without URLs
        """
        if not text:
            return ""

        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

        return text

    @staticmethod
    def remove_extra_symbols(text: str) -> str:
        """
        Remove extra symbols and special characters.

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove excessive punctuation
        text = re.sub(r'[!?。！？]{2,}', '。', text)

        # Remove special symbols but keep Chinese characters, letters, numbers, and basic punctuation
        text = re.sub(r"[^\w\s\u4e00-\u9fff.,!?;:()（），。！？；：、\[\]【】\"\"''\-]", '', text)

        return text

    @classmethod
    def clean_article_text(cls, text: str, remove_urls_flag: bool = True) -> str:
        """
        Full cleaning pipeline for article text.

        Args:
            text: Raw article text (may contain HTML)
            remove_urls_flag: Whether to remove URLs

        Returns:
            Cleaned and normalized text
        """
        if not text:
            return ""

        # Remove HTML
        text = cls.clean_html(text)

        # Remove URLs if requested
        if remove_urls_flag:
            text = cls.remove_urls(text)

        # Normalize whitespace
        text = cls.normalize_whitespace(text)

        # Remove extra symbols
        text = cls.remove_extra_symbols(text)

        # Final whitespace normalization
        text = cls.normalize_whitespace(text)

        return text

    @staticmethod
    def extract_summary(text: str, max_length: int = 200) -> str:
        """
        Extract summary from text (first N characters).

        Args:
            text: Full text
            max_length: Maximum summary length

        Returns:
            Text summary
        """
        if not text:
            return ""

        # Clean text first
        text = TextProcessor.clean_article_text(text)

        # Take first max_length characters
        if len(text) <= max_length:
            return text

        # Try to cut at sentence boundary
        summary = text[:max_length]
        last_period = max(
            summary.rfind('。'),
            summary.rfind('.'),
            summary.rfind('！'),
            summary.rfind('？')
        )

        if last_period > max_length * 0.5:  # At least 50% of desired length
            summary = summary[:last_period + 1]
        else:
            summary = summary + '...'

        return summary

    @staticmethod
    def handle_encoding(text: str, source_encoding: Optional[str] = None) -> str:
        """
        Handle various Chinese encodings.

        Args:
            text: Input text (may be bytes or str)
            source_encoding: Source encoding (auto-detect if None)

        Returns:
            UTF-8 encoded string
        """
        if isinstance(text, bytes):
            # Try common Chinese encodings
            encodings = [source_encoding] if source_encoding else ['utf-8', 'gbk', 'gb2312', 'gb18030']

            for encoding in encodings:
                try:
                    return text.decode(encoding)
                except (UnicodeDecodeError, AttributeError, LookupError):
                    continue

            # Fallback to utf-8 with error handling
            return text.decode('utf-8', errors='ignore')

        return text

    @staticmethod
    def is_valid_article(text: str, min_length: int = 50) -> bool:
        """
        Check if text is a valid article (not too short).

        Args:
            text: Article text
            min_length: Minimum required length

        Returns:
            True if valid article
        """
        if not text:
            return False

        cleaned = TextProcessor.clean_article_text(text)
        return len(cleaned) >= min_length


# Global text processor instance
text_processor = TextProcessor()
