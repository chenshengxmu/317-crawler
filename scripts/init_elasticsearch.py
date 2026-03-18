"""
Initialize Elasticsearch index with proper Chinese text analyzer configuration.
Run this script after starting Elasticsearch and installing the IK Analysis plugin.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from storage import es_client, index_manager


def main():
    """Initialize Elasticsearch index."""
    logger.info("Starting Elasticsearch initialization...")

    try:
        # Test connection
        logger.info("Testing Elasticsearch connection...")
        health = es_client.health_check()
        logger.info(f"Elasticsearch health: {health}")

        if health.get("status") == "error":
            logger.error("Elasticsearch is not available. Please start it first.")
            return False

        # Verify IK analyzer
        logger.info("Verifying IK analyzer...")
        if not index_manager.verify_ik_analyzer():
            logger.error(
                "IK analyzer not found! Please install it:\n"
                "docker exec -it news-crawler-elasticsearch /usr/share/elasticsearch/bin/elasticsearch-plugin "
                "install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v8.12.0/"
                "elasticsearch-analysis-ik-8.12.0.zip\n"
                "docker restart news-crawler-elasticsearch"
            )
            return False

        # Create index
        logger.info("Creating news articles index...")
        if index_manager.create_index(delete_if_exists=False):
            logger.success("Index created successfully!")

            # Show index stats
            stats = index_manager.get_index_stats()
            logger.info(f"Index stats: {stats}")

            return True
        else:
            logger.error("Failed to create index")
            return False

    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
