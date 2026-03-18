"""
Elasticsearch index management with Chinese text analyzer support.
Creates and manages the news_articles index with proper mappings.
"""

from typing import Dict, Any
from loguru import logger

from config import settings
from .elasticsearch_client import es_client


class IndexManager:
    """Manage Elasticsearch index creation and configuration."""

    def __init__(self, index_name: str = None):
        """
        Initialize index manager.

        Args:
            index_name: Index name (defaults to settings.es_index)
        """
        self.index_name = index_name or settings.es_index

    @property
    def client(self):
        return es_client.get_client()

    def get_index_mapping(self) -> Dict[str, Any]:
        """
        Get index mapping with Chinese text analyzers.

        Returns:
            Index mapping configuration
        """
        return {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "chinese_analyzer": {
                            "type": "custom",
                            "tokenizer": "ik_max_word",
                            "filter": ["lowercase"],
                        },
                        "chinese_search_analyzer": {
                            "type": "custom",
                            "tokenizer": "ik_smart",
                            "filter": ["lowercase"],
                        },
                    }
                },
            },
            "mappings": {
                "properties": {
                    # Article content fields with Chinese analyzers
                    "title": {
                        "type": "text",
                        "analyzer": "chinese_analyzer",
                        "search_analyzer": "chinese_search_analyzer",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            }
                        }
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "chinese_analyzer",
                        "search_analyzer": "chinese_search_analyzer",
                    },
                    "summary": {
                        "type": "text",
                        "analyzer": "chinese_analyzer",
                        "search_analyzer": "chinese_search_analyzer",
                    },
                    # Metadata fields
                    "source": {
                        "type": "keyword"
                    },
                    "category": {
                        "type": "keyword"
                    },
                    "author": {
                        "type": "keyword"
                    },
                    "tags": {
                        "type": "keyword"
                    },
                    # Date fields
                    "publish_time": {
                        "type": "date",
                        "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis"
                    },
                    "crawl_time": {
                        "type": "date",
                        "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd||epoch_millis"
                    },
                    # URL and hash fields for deduplication
                    "url": {
                        "type": "keyword"
                    },
                    "url_hash": {
                        "type": "keyword"
                    },
                    "content_hash": {
                        "type": "keyword"
                    },
                    # Images (not indexed, just stored)
                    "images": {
                        "type": "keyword",
                        "index": False
                    },
                }
            }
        }

    def create_index(self, delete_if_exists: bool = False) -> bool:
        """
        Create the news articles index.

        Args:
            delete_if_exists: If True, delete existing index before creating

        Returns:
            True if index created successfully
        """
        try:
            # Check if index exists
            if self.client.indices.exists(index=self.index_name):
                if delete_if_exists:
                    logger.warning(f"Deleting existing index: {self.index_name}")
                    self.client.indices.delete(index=self.index_name)
                else:
                    logger.info(f"Index already exists: {self.index_name}")
                    return True

            # Create index with mapping
            mapping = self.get_index_mapping()
            self.client.indices.create(index=self.index_name, **mapping)
            logger.info(f"Created index: {self.index_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False

    def delete_index(self) -> bool:
        """
        Delete the index.

        Returns:
            True if deleted successfully
        """
        try:
            if self.client.indices.exists(index=self.index_name):
                self.client.indices.delete(index=self.index_name)
                logger.info(f"Deleted index: {self.index_name}")
                return True
            else:
                logger.warning(f"Index does not exist: {self.index_name}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            return False

    def index_exists(self) -> bool:
        """
        Check if index exists.

        Returns:
            True if index exists
        """
        try:
            return self.client.indices.exists(index=self.index_name)
        except Exception as e:
            logger.error(f"Failed to check index existence: {e}")
            return False

    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Index statistics
        """
        try:
            stats = self.client.indices.stats(index=self.index_name)
            return {
                "document_count": stats["_all"]["primaries"]["docs"]["count"],
                "store_size": stats["_all"]["primaries"]["store"]["size_in_bytes"],
                "index_name": self.index_name,
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {}

    def verify_ik_analyzer(self) -> bool:
        """
        Verify IK analyzer is installed and working.

        Returns:
            True if IK analyzer is available
        """
        try:
            # Test IK analyzer with sample Chinese text
            result = self.client.indices.analyze(
                analyzer="ik_max_word",
                text="中国人工智能技术发展迅速"
            )
            tokens = [token["token"] for token in result["tokens"]]
            logger.info(f"IK analyzer test successful. Tokens: {tokens}")
            return len(tokens) > 0
        except Exception as e:
            logger.error(f"IK analyzer not available: {e}")
            return False

    def refresh_index(self):
        """Refresh the index to make recent changes searchable."""
        try:
            self.client.indices.refresh(index=self.index_name)
            logger.debug(f"Refreshed index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to refresh index: {e}")


# Global index manager instance
index_manager = IndexManager()
