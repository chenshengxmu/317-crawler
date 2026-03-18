"""
Elasticsearch connection management and operations.
Provides CRUD operations with retry logic and connection pooling.
"""

import time
from typing import Dict, List, Optional, Any
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import ConnectionError, TransportError
from loguru import logger

from config import settings


class ElasticsearchClient:
    """Elasticsearch client with connection management and CRUD operations."""

    def __init__(self, max_retries: int = 3, retry_delay: int = 2):
        """
        Initialize Elasticsearch client.

        Args:
            max_retries: Maximum number of connection retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: Optional[Elasticsearch] = None

    def connect(self) -> Elasticsearch:
        """
        Establish connection to Elasticsearch with retry logic.

        Returns:
            Elasticsearch client instance

        Raises:
            ConnectionError: If connection fails after all retries
        """
        if self._client is not None:
            return self._client

        for attempt in range(1, self.max_retries + 1):
            try:
                # Build connection parameters
                es_params = {
                    "hosts": [settings.es_url],
                    "request_timeout": 30,
                    "max_retries": 3,
                    "retry_on_timeout": True,
                }

                # Add authentication if configured
                if settings.es_username and settings.es_password:
                    es_params["basic_auth"] = (settings.es_username, settings.es_password)

                self._client = Elasticsearch(**es_params)

                # Test connection
                if self._client.ping():
                    logger.info(f"Connected to Elasticsearch at {settings.es_url}")
                    return self._client
                else:
                    raise ConnectionError("Ping failed")

            except Exception as e:
                logger.warning(
                    f"Elasticsearch connection attempt {attempt}/{self.max_retries} failed: {e}"
                )
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logger.error("Failed to connect to Elasticsearch after all retries")
                    raise

        raise ConnectionError("Failed to connect to Elasticsearch")

    def get_client(self) -> Elasticsearch:
        """Get or create Elasticsearch client."""
        if self._client is None:
            return self.connect()
        return self._client

    def health_check(self) -> Dict[str, Any]:
        """
        Check Elasticsearch cluster health.

        Returns:
            Health status information
        """
        try:
            client = self.get_client()
            health = client.cluster.health()
            return {
                "status": health["status"],
                "cluster_name": health["cluster_name"],
                "number_of_nodes": health["number_of_nodes"],
                "active_shards": health["active_shards"],
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def index_document(
        self, index: str, document: Dict[str, Any], doc_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Index a single document.

        Args:
            index: Index name
            document: Document to index
            doc_id: Optional document ID (auto-generated if not provided)

        Returns:
            Indexing result
        """
        try:
            client = self.get_client()
            result = client.index(index=index, id=doc_id, document=document)
            logger.debug(f"Indexed document to {index}: {result['_id']}")
            return result
        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            raise

    def bulk_index(self, index: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Bulk index multiple documents.

        Args:
            index: Index name
            documents: List of documents to index

        Returns:
            Bulk indexing result with success/failure counts
        """
        if not documents:
            return {"success": 0, "failed": 0}

        try:
            client = self.get_client()

            # Prepare bulk actions
            actions = [
                {
                    "_index": index,
                    "_id": doc.get("_id"),
                    "_source": {k: v for k, v in doc.items() if k != "_id"},
                }
                for doc in documents
            ]

            # Execute bulk operation
            success, failed = helpers.bulk(
                client, actions, raise_on_error=False, stats_only=False
            )

            logger.info(f"Bulk indexed {success} documents to {index}, {len(failed)} failed")
            return {"success": success, "failed": len(failed), "errors": failed}

        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            raise

    def get_document(self, index: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.

        Args:
            index: Index name
            doc_id: Document ID

        Returns:
            Document if found, None otherwise
        """
        try:
            client = self.get_client()
            result = client.get(index=index, id=doc_id)
            return result["_source"]
        except Exception as e:
            logger.debug(f"Document not found: {doc_id} - {e}")
            return None

    def search(
        self,
        index: str,
        query: Dict[str, Any],
        size: int = 10,
        from_: int = 0,
        sort: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a search query.

        Args:
            index: Index name
            query: Elasticsearch query DSL
            size: Number of results to return
            from_: Offset for pagination
            sort: Sort criteria

        Returns:
            Search results
        """
        try:
            client = self.get_client()
            body = {"query": query, "size": size, "from": from_}

            if sort:
                body["sort"] = sort

            result = client.search(index=index, **body)
            return result
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def count(self, index: str, query: Optional[Dict[str, Any]] = None) -> int:
        """
        Count documents matching a query.

        Args:
            index: Index name
            query: Optional query (counts all if not provided)

        Returns:
            Document count
        """
        try:
            client = self.get_client()
            if query:
                result = client.count(index=index, query=query)
            else:
                result = client.count(index=index)
            return result["count"]
        except Exception as e:
            logger.error(f"Count failed: {e}")
            return 0

    def delete_document(self, index: str, doc_id: str) -> bool:
        """
        Delete a document by ID.

        Args:
            index: Index name
            doc_id: Document ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            client = self.get_client()
            client.delete(index=index, id=doc_id)
            logger.debug(f"Deleted document {doc_id} from {index}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False

    def close(self):
        """Close Elasticsearch connection."""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Elasticsearch connection closed")


# Global client instance
es_client = ElasticsearchClient()
