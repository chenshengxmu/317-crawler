"""
Manual crawler execution script for testing and debugging.
Allows running specific spiders or all spiders.
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from loguru import logger

from utils import setup_logger


def run_spider(spider_name: str = None, output_file: str = None):
    """
    Run a specific spider or all spiders.

    Args:
        spider_name: Name of spider to run (None for all spiders)
        output_file: Optional output file for results
    """
    # Setup logger
    setup_logger('crawler.log')

    # Get Scrapy settings
    settings = get_project_settings()

    # Add output file if specified
    if output_file:
        settings.set('FEEDS', {
            output_file: {
                'format': 'json',
                'encoding': 'utf-8',
                'indent': 2,
            }
        })

    # Create crawler process
    process = CrawlerProcess(settings)

    # Available spiders
    available_spiders = ['sina', 'sina_tech', 'url_list']

    if spider_name:
        if spider_name not in available_spiders:
            logger.error(f"Unknown spider: {spider_name}")
            logger.info(f"Available spiders: {', '.join(available_spiders)}")
            return False

        logger.info(f"Starting spider: {spider_name}")
        process.crawl(spider_name)
    else:
        logger.info(f"Starting all spiders: {', '.join(available_spiders)}")
        for spider in available_spiders:
            process.crawl(spider)

    # Start crawling
    try:
        process.start()
        logger.success("Crawling completed successfully")
        return True
    except Exception as e:
        logger.error(f"Crawling failed: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run news crawler spiders')
    parser.add_argument(
        '--spider',
        '-s',
        type=str,
        help='Spider name to run (sina, netease, tencent). If not specified, runs all spiders.'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        help='Output file for results (JSON format)'
    )

    args = parser.parse_args()

    success = run_spider(spider_name=args.spider, output_file=args.output)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
