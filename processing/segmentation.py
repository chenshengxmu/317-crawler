"""
Chinese text segmentation using Jieba.
Provides word segmentation and keyword extraction for better search indexing.
"""

from typing import List, Dict
import jieba
import jieba.analyse
from loguru import logger


class ChineseSegmenter:
    """Chinese text segmentation and keyword extraction."""

    def __init__(self, custom_dict_path: str = None):
        """
        Initialize Chinese segmenter.

        Args:
            custom_dict_path: Path to custom dictionary file (optional)
        """
        self.initialized = False
        self.custom_dict_path = custom_dict_path
        self._initialize()

    def _initialize(self):
        """Initialize Jieba with custom dictionary if provided."""
        try:
            if self.custom_dict_path:
                jieba.load_userdict(self.custom_dict_path)
                logger.info(f"Loaded custom dictionary: {self.custom_dict_path}")

            self.initialized = True
            logger.info("Chinese segmenter initialized")

        except Exception as e:
            logger.error(f"Failed to initialize segmenter: {e}")
            self.initialized = False

    def segment(self, text: str, cut_all: bool = False) -> List[str]:
        """
        Segment Chinese text into words.

        Args:
            text: Input text
            cut_all: If True, use full mode (more segments)

        Returns:
            List of word segments
        """
        if not text:
            return []

        try:
            segments = jieba.cut(text, cut_all=cut_all)
            return [seg.strip() for seg in segments if seg.strip()]
        except Exception as e:
            logger.error(f"Segmentation failed: {e}")
            return []

    def segment_for_search(self, text: str) -> List[str]:
        """
        Segment text for search (uses search mode).

        Args:
            text: Input text

        Returns:
            List of word segments optimized for search
        """
        if not text:
            return []

        try:
            segments = jieba.cut_for_search(text)
            return [seg.strip() for seg in segments if seg.strip()]
        except Exception as e:
            logger.error(f"Search segmentation failed: {e}")
            return []

    def extract_keywords(
        self,
        text: str,
        top_k: int = 10,
        with_weight: bool = False,
        allowed_pos: tuple = ('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vn')
    ) -> List[str] | List[tuple]:
        """
        Extract keywords using TF-IDF.

        Args:
            text: Input text
            top_k: Number of keywords to extract
            with_weight: If True, return (word, weight) tuples
            allowed_pos: Allowed part-of-speech tags

        Returns:
            List of keywords or (keyword, weight) tuples
        """
        if not text:
            return []

        try:
            keywords = jieba.analyse.extract_tags(
                text,
                topK=top_k,
                withWeight=with_weight,
                allowPOS=allowed_pos
            )
            return keywords
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return []

    def extract_keywords_textrank(
        self,
        text: str,
        top_k: int = 10,
        with_weight: bool = False,
        allowed_pos: tuple = ('n', 'nr', 'ns', 'nt', 'nz', 'v', 'vn')
    ) -> List[str] | List[tuple]:
        """
        Extract keywords using TextRank algorithm.

        Args:
            text: Input text
            top_k: Number of keywords to extract
            with_weight: If True, return (word, weight) tuples
            allowed_pos: Allowed part-of-speech tags

        Returns:
            List of keywords or (keyword, weight) tuples
        """
        if not text:
            return []

        try:
            keywords = jieba.analyse.textrank(
                text,
                topK=top_k,
                withWeight=with_weight,
                allowPOS=allowed_pos
            )
            return keywords
        except Exception as e:
            logger.error(f"TextRank extraction failed: {e}")
            return []

    def add_word(self, word: str, freq: int = None, tag: str = None):
        """
        Add a word to the dictionary.

        Args:
            word: Word to add
            freq: Word frequency (optional)
            tag: Part-of-speech tag (optional)
        """
        try:
            if freq and tag:
                jieba.add_word(word, freq, tag)
            elif freq:
                jieba.add_word(word, freq)
            else:
                jieba.add_word(word)
            logger.debug(f"Added word to dictionary: {word}")
        except Exception as e:
            logger.error(f"Failed to add word: {e}")

    def get_word_stats(self, text: str) -> Dict[str, int]:
        """
        Get word frequency statistics.

        Args:
            text: Input text

        Returns:
            Dictionary of word frequencies
        """
        if not text:
            return {}

        segments = self.segment(text)
        word_freq = {}

        for word in segments:
            if len(word) > 1:  # Skip single characters
                word_freq[word] = word_freq.get(word, 0) + 1

        return dict(sorted(word_freq.items(), key=lambda x: x[1], reverse=True))


# Global segmenter instance
chinese_segmenter = ChineseSegmenter()
