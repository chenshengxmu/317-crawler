"""
Scheduled crawling tasks.
Defines tasks for periodic execution of spiders.
"""

from datetime import datetime
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import reactor, defer
from loguru import logger


class CrawlerTask:
    """Manages scheduled crawler execution."""

    def __init__(self):
        """Initialize crawler task."""
        self.settings = get_project_settings()
        self.runner = None
        self.stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'last_run': None,
            'last_status': None,
        }

    @defer.inlineCallbacks
    def run_spiders(self, spider_names=None):
        """
        Run specified spiders or all spiders.

        Args:
            spider_names: List of spider names to run (None for all)
        """
        if spider_names is None:
            spider_names = ['sina']  # Add more: 'netease', 'tencent'

        logger.info(f"Starting scheduled crawl: {', '.join(spider_names)}")
        start_time = datetime.now()

        try:
            # Create new runner for this execution
            self.runner = CrawlerRunner(self.settings)

            # Run spiders sequentially
            for spider_name in spider_names:
                logger.info(f"Running spider: {spider_name}")
                yield self.runner.crawl(spider_name)

            # Update stats
            self.stats['total_runs'] += 1
            self.stats['successful_runs'] += 1
            self.stats['last_status'] = 'success'

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.success(f"Scheduled crawl completed successfully in {elapsed:.2f}s")

        except Exception as e:
            self.stats['total_runs'] += 1
            self.stats['failed_runs'] += 1
            self.stats['last_status'] = 'failed'
            logger.error(f"Scheduled crawl failed: {e}")

        finally:
            self.stats['last_run'] = datetime.now().isoformat()

    def get_stats(self):
        """Get crawler statistics."""
        return self.stats


# Global crawler task instance
crawler_task = CrawlerTask()


def run_crawler_job():
    """
    Job function for scheduler.
    Runs all spiders in a separate reactor.
    """
    logger.info("Crawler job triggered")

    # Note: In production, you may want to run this in a subprocess
    # to avoid blocking the main thread
    try:
        from twisted.internet import reactor
        from scrapy.crawler import CrawlerProcess

        settings = get_project_settings()
        process = CrawlerProcess(settings)

        # Add spiders
        process.crawl('sina')
        # Add more spiders as they are implemented
        # process.crawl('netease')
        # process.crawl('tencent')

        # Start crawling (blocking)
        process.start()

        logger.info("Crawler job completed")

    except Exception as e:
        logger.error(f"Crawler job failed: {e}")
