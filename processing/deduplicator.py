"""
Deduplication utilities for detecting duplicate articles.
Uses URL hashing and content hashing for efficient duplicate detection.
"""

import hashlib
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from loguru import logger

from storage import es_client
from config import settings


class Deduplicator:
    """Detect and prevent duplicate articles."""

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URL by removing tracking parameters and fragments.

        Args:
            url: Original URL

        Returns:
            Normalized URL
        """
        if not url:
            return ""

        try:
            parsed = urlparse(url)

            # Remove common tracking parameters
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'from', 'spm', 'ref', 'source', 'share', 'timestamp'
            }

            # Parse query parameters
            query_params = parse_qs(parsed.query)

            # Filter out tracking parameters
            cleaned_params = {
                k: v for k, v in query_params.items()
                if k.lower() not in tracking_params
            }

            # Rebuild query string
            new_query = urlencode(cleaned_params, doseq=True)

            # Reconstruct URL without fragment
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc.lower(),
                parsed.path,
                parsed.params,
                new_query,
                ''  # Remove fragment
            ))

            return normalized

        except Exception as e:
            logger.warning(f"URL normalization failed: {e}")
            return url

    @staticmethod
    def generate_url_hash(url: str) -> str:
        """
        Generate MD5 hash of normalized URL.

        Args:
            url: Article URL

        Returns:
            MD5 hash of URL
        """
        normalized_url = Deduplicator.normalize_url(url)
        return hashlib.md5(normalized_url.encode('utf-8')).hexdigest()

    @staticmethod
    def generate_content_hash(content: str) -> str:
        """
        Generate MD5 hash of normalized content.

        Args:
            content: Article content

        Returns:
            MD5 hash of content
        """
        if not content:
            return ""

        # Normalize content: remove whitespace and convert to lowercase
        normalized = ''.join(content.split()).lower()
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()

    @staticmethod
    def check_url_exists(url_hash: str) -> bool:
        """
        Check if URL hash already exists in Elasticsearch.

        Args:
            url_hash: URL hash to check

        Returns:
            True if URL exists
        """
        try:
            query = {
                "term": {
                    "url_hash": url_hash
                }
            }

            result = es_client.search(
                index=settings.es_index,
                query=query,
                size=1
            )

            return result['hits']['total']['value'] > 0

        except Exception as e:
            logger.error(f"Failed to check URL existence: {e}")
            return False

    @staticmethod
    def check_content_exists(content_hash: str) -> bool:
        """
        Check if content hash already exists in Elasticsearch.

        Args:
            content_hash: Content hash to check

        Returns:
            True if content exists
        """
        try:
            query = {
                "term": {
                    "content_hash": content_hash
                }
            }

            result = es_client.search(
                index=settings.es_index,
                query=query,
                size=1
            )

            return result['hits']['total']['value'] > 0

        except Exception as e:
            logger.error(f"Failed to check content existence: {e}")
            return False

    @staticmethod
    def is_duplicate(url: str, content: str) -> tuple[bool, str]:
        """
        Check if article is duplicate by URL or content.

        Args:
            url: Article URL
            content: Article content

        Returns:
            Tuple of (is_duplicate, reason)
        """
        # Generate hashes
        url_hash = Deduplicator.generate_url_hash(url)
        content_hash = Deduplicator.generate_content_hash(content)

        # Check URL duplicate
        if Deduplicator.check_url_exists(url_hash):
            return True, "duplicate_url"

        # Check content duplicate
        if Deduplicator.check_content_exists(content_hash):
            return True, "duplicate_content"

        return False, ""

    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """
        Calculate simple similarity between two texts using character overlap.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        if not text1 or not text2:
            return 0.0

        # Convert to character sets
        set1 = set(text1)
        set2 = set(text2)

        # Calculate Jaccard similarity
        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 0.0

        return intersection / union


# Global deduplicator instance
deduplicator = Deduplicator()
