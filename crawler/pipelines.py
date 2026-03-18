"""
Scrapy pipelines for processing and storing news articles.
Includes validation, cleaning, deduplication, and Elasticsearch storage.
"""

from datetime import datetime
from typing import Dict, List
from loguru import logger

from crawler.items import NewsArticle
from processing import text_processor, deduplicator
from storage import es_client
from config import settings


class ValidationPipeline:
    """Validate required fields in articles."""

    def process_item(self, item: NewsArticle):
        """
        Validate article item.

        Args:
            item: NewsArticle item
            spider: Spider instance

        Returns:
            Validated item

        Raises:
            DropItem: If validation fails
        """
        required_fields = ['title', 'content', 'url']

        for field in required_fields:
            if not item.get(field):
                logger.warning(f"Missing required field '{field}' in item: {item.get('url', 'unknown')}")
                from scrapy.exceptions import DropItem
                raise DropItem(f"Missing required field: {field}")

        # Validate content length
        if len(item['content']) < 100:
            logger.warning(f"Content too short: {item['url']}")
            from scrapy.exceptions import DropItem
            raise DropItem("Content too short")

        return item


class TextCleaningPipeline:
    """Clean and normalize text fields."""

    def process_item(self, item: NewsArticle):
        """
        Clean text fields.

        Args:
            item: NewsArticle item
            spider: Spider instance

        Returns:
            Cleaned item
        """
        # Clean title
        if item.get('title'):
            item['title'] = text_processor.clean_article_text(item['title'], remove_urls_flag=False)

        # Clean content (already cleaned in spider, but ensure consistency)
        if item.get('content'):
            item['content'] = text_processor.clean_article_text(item['content'])

        # Generate or clean summary
        if not item.get('summary') and item.get('content'):
            item['summary'] = text_processor.extract_summary(item['content'], max_length=200)
        elif item.get('summary'):
            item['summary'] = text_processor.clean_article_text(item['summary'], remove_urls_flag=False)

        return item


class DeduplicationPipeline:
    """Check for duplicate articles."""

    def __init__(self):
        self.seen_urls = set()
        self.seen_content = set()

    def process_item(self, item: NewsArticle):
        """
        Check for duplicates.

        Args:
            item: NewsArticle item
            spider: Spider instance

        Returns:
            Item if not duplicate

        Raises:
            DropItem: If duplicate found
        """
        url_hash = item.get('url_hash')
        content_hash = item.get('content_hash')

        # Check in-memory cache first (for current crawl session)
        if url_hash in self.seen_urls:
            logger.debug(f"Duplicate URL in session: {item['url']}")
            from scrapy.exceptions import DropItem
            raise DropItem("Duplicate URL in session")

        if content_hash in self.seen_content:
            logger.debug(f"Duplicate content in session: {item['url']}")
            from scrapy.exceptions import DropItem
            raise DropItem("Duplicate content in session")

        # Check Elasticsearch
        is_duplicate, reason = deduplicator.is_duplicate(item['url'], item['content'])
        if is_duplicate:
            logger.debug(f"Duplicate found in ES ({reason}): {item['url']}")
            from scrapy.exceptions import DropItem
            raise DropItem(f"Duplicate: {reason}")

        # Add to seen sets
        self.seen_urls.add(url_hash)
        self.seen_content.add(content_hash)

        return item


class ElasticsearchPipeline:
    """Store articles in Elasticsearch."""

    def __init__(self):
        self.client = None
        self.buffer: List[Dict] = []
        self.buffer_size = 100  # Bulk insert every 100 items
        self.stats = {
            'success': 0,
            'failed': 0,
        }

    def open_spider(self):
        """Initialize Elasticsearch connection when spider opens."""
        try:
            self.client = es_client.get_client()
            logger.info("Elasticsearch pipeline initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch pipeline: {e}")
            raise

    def close_spider(self):
        """Flush remaining items when spider closes."""
        if self.buffer:
            self._flush_buffer()

        logger.info(
            f"Elasticsearch pipeline closed. "
            f"Success: {self.stats['success']}, Failed: {self.stats['failed']}"
        )

    def process_item(self, item: NewsArticle):
        """
        Add item to buffer and flush when full.

        Args:
            item: NewsArticle item
            spider: Spider instance

        Returns:
            Processed item
        """
        # Convert item to dict
        doc = dict(item)

        # Add document ID (use url_hash)
        doc['_id'] = doc.get('url_hash')

        # Add to buffer
        self.buffer.append(doc)

        # Flush if buffer is full
        if len(self.buffer) >= self.buffer_size:
            self._flush_buffer()

        return item

    def _flush_buffer(self):
        """Flush buffer to Elasticsearch."""
        if not self.buffer:
            return

        try:
            result = es_client.bulk_index(settings.es_index, self.buffer)
            self.stats['success'] += result['success']
            self.stats['failed'] += result['failed']

            logger.info(
                f"Flushed {len(self.buffer)} items to ES. "
                f"Success: {result['success']}, Failed: {result['failed']}"
            )

            # Clear buffer
            self.buffer = []

        except Exception as e:
            logger.error(f"Failed to flush buffer to Elasticsearch: {e}")
            self.stats['failed'] += len(self.buffer)
            self.buffer = []


class StatsPipeline:
    """Collect crawling statistics."""

    def __init__(self):
        self.stats = {
            'total': 0,
            'by_source': {},
            'by_category': {},
        }

    def process_item(self, item: NewsArticle):
        """
        Update statistics.

        Args:
            item: NewsArticle item
            spider: Spider instance

        Returns:
            Item
        """
        self.stats['total'] += 1

        # Count by source
        source = item.get('source', 'unknown')
        self.stats['by_source'][source] = self.stats['by_source'].get(source, 0) + 1

        # Count by category
        category = item.get('category', 'unknown')
        self.stats['by_category'][category] = self.stats['by_category'].get(category, 0) + 1

        return item

    def close_spider(self):
        """Log statistics when spider closes."""
        logger.info(f"Crawling statistics: {self.stats}")
