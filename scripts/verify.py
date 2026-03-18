"""
Verification script to check if all components are working correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
from loguru import logger
from storage import es_client, index_manager
from processing import text_processor, chinese_segmenter, deduplicator
from config import settings


def check_elasticsearch():
    """Check Elasticsearch connection and health."""
    logger.info("Checking Elasticsearch...")
    try:
        health = es_client.health_check()
        if health.get('status') == 'error':
            logger.error("❌ Elasticsearch is not healthy")
            return False

        logger.success(f"✓ Elasticsearch is healthy: {health}")

        # Check IK analyzer
        if index_manager.verify_ik_analyzer():
            logger.success("✓ IK analyzer is working")
        else:
            logger.error("❌ IK analyzer is not available")
            return False

        # Check index
        if index_manager.index_exists():
            stats = index_manager.get_index_stats()
            logger.success(f"✓ Index exists: {stats}")
        else:
            logger.warning("⚠ Index does not exist (run init_elasticsearch.py)")

        return True

    except Exception as e:
        logger.error(f"❌ Elasticsearch check failed: {e}")
        return False


def check_text_processing():
    """Check text processing modules."""
    logger.info("Checking text processing...")
    try:
        # Test text cleaning
        html = '<p>这是<strong>测试</strong>文本</p>'
        cleaned = text_processor.clean_article_text(html)
        assert '测试' in cleaned
        logger.success("✓ Text cleaning works")

        # Test Chinese segmentation
        segments = chinese_segmenter.segment("中国人工智能技术发展迅速")
        assert len(segments) > 0
        logger.success(f"✓ Chinese segmentation works: {segments}")

        # Test keyword extraction
        keywords = chinese_segmenter.extract_keywords("人工智能技术在中国发展迅速，应用广泛", top_k=5)
        assert len(keywords) > 0
        logger.success(f"✓ Keyword extraction works: {keywords}")

        # Test deduplication
        url_hash = deduplicator.generate_url_hash("https://example.com/test")
        content_hash = deduplicator.generate_content_hash("测试内容")
        assert len(url_hash) == 32
        assert len(content_hash) == 32
        logger.success("✓ Deduplication works")

        return True

    except Exception as e:
        logger.error(f"❌ Text processing check failed: {e}")
        return False


def check_api():
    """Check if API server is running."""
    logger.info("Checking API server...")
    try:
        host = "localhost" if settings.api_host == "0.0.0.0" else settings.api_host
        response = requests.get(f"http://{host}:{settings.api_port}/api/v1/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            logger.success(f"✓ API server is running: {data}")
            return True
        else:
            logger.warning(f"⚠ API returned status {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        logger.warning("⚠ API server is not running (start with: make api)")
        return False
    except Exception as e:
        logger.error(f"❌ API check failed: {e}")
        return False


def check_configuration():
    """Check configuration."""
    logger.info("Checking configuration...")
    try:
        logger.info(f"  ES URL: {settings.es_url}")
        logger.info(f"  ES Index: {settings.es_index}")
        logger.info(f"  API: {settings.api_host}:{settings.api_port}")
        logger.info(f"  Environment: {settings.environment}")
        logger.info(f"  Log Level: {settings.log_level}")
        logger.success("✓ Configuration loaded")
        return True
    except Exception as e:
        logger.error(f"❌ Configuration check failed: {e}")
        return False


def main():
    """Run all verification checks."""
    logger.info("=" * 50)
    logger.info("News Crawler - System Verification")
    logger.info("=" * 50)
    logger.info("")

    results = {
        "Configuration": check_configuration(),
        "Elasticsearch": check_elasticsearch(),
        "Text Processing": check_text_processing(),
        "API Server": check_api(),
    }

    logger.info("")
    logger.info("=" * 50)
    logger.info("Verification Results:")
    logger.info("=" * 50)

    all_passed = True
    for component, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        logger.info(f"  {component}: {status}")
        if not passed:
            all_passed = False

    logger.info("")

    if all_passed:
        logger.success("All checks passed! System is ready.")
        return 0
    else:
        logger.warning("Some checks failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
