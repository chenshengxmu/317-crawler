"""
APScheduler-based scheduler for automated crawling.
Schedules periodic execution of news spiders.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from datetime import datetime

from config import settings
from utils import setup_logger
from scheduler.tasks import run_crawler_job


def main():
    """Main scheduler entry point."""
    # Setup logger
    setup_logger('scheduler.log')

    logger.info("Starting News Crawler Scheduler...")
    logger.info(f"Scheduler enabled: {settings.scheduler_enabled}")
    logger.info(f"Crawl interval: {settings.scheduler_interval_minutes} minutes")

    if not settings.scheduler_enabled:
        logger.warning("Scheduler is disabled in configuration")
        return

    # Create scheduler
    scheduler = BlockingScheduler()

    # Add job - run crawler every N minutes
    scheduler.add_job(
        run_crawler_job,
        trigger=IntervalTrigger(minutes=settings.scheduler_interval_minutes),
        id='crawler_job',
        name='Run news crawlers',
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
        coalesce=True,  # Combine missed runs
    )

    # Optional: Add specific time-based schedules
    # Example: Run Sina spider at specific times
    # scheduler.add_job(
    #     lambda: run_crawler_job(),
    #     trigger=CronTrigger(hour='0,6,12,18', minute=0),  # Every 6 hours
    #     id='sina_scheduled',
    #     name='Sina scheduled crawl',
    # )

    # Log scheduled jobs
    logger.info("Scheduled jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name} (ID: {job.id}): {job.trigger}")

    # Start scheduler
    try:
        logger.success("Scheduler started successfully")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        raise


if __name__ == '__main__':
    main()
