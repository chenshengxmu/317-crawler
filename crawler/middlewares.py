"""
Scrapy middlewares for custom request/response processing.
Includes user agent rotation, rate limiting, and retry logic.
"""

import time
from fake_useragent import UserAgent
from loguru import logger


class RotateUserAgentMiddleware:
    """Rotate user agents to avoid blocking."""

    def __init__(self):
        self.ua = UserAgent()

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request):
        """Set random user agent for each request."""
        try:
            request.headers['User-Agent'] = self.ua.random
        except Exception as e:
            logger.warning(f"Failed to set random user agent: {e}")
            request.headers['User-Agent'] = (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )


class RateLimitMiddleware:
    """Enforce rate limiting between requests."""

    def __init__(self, delay=0.5):
        self.delay = delay
        self.last_request_time = {}

    @classmethod
    def from_crawler(cls, crawler):
        delay = crawler.settings.getfloat('DOWNLOAD_DELAY', 0.5)
        return cls(delay=delay)

    def process_request(self, request):
        """Enforce delay between requests to same domain."""
        domain = request.url.split('/')[2]

        if domain in self.last_request_time:
            elapsed = time.time() - self.last_request_time[domain]
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)

        self.last_request_time[domain] = time.time()


class RetryMiddleware:
    """Custom retry logic with exponential backoff."""

    def __init__(self, max_retries=3, retry_delay=2):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @classmethod
    def from_crawler(cls, crawler):
        max_retries = crawler.settings.getint('RETRY_TIMES', 3)
        return cls(max_retries=max_retries)

    def process_response(self, request, response):
        """Process response and retry if needed."""
        if response.status in [500, 502, 503, 504, 408, 429]:
            retry_count = request.meta.get('retry_count', 0)

            if retry_count < self.max_retries:
                logger.warning(
                    f"Retrying {request.url} (attempt {retry_count + 1}/{self.max_retries}) "
                    f"due to status {response.status}"
                )
                delay = self.retry_delay * (2 ** retry_count)
                time.sleep(delay)

                retry_request = request.copy()
                retry_request.meta['retry_count'] = retry_count + 1
                retry_request.dont_filter = True
                return retry_request

            logger.error(f"Max retries reached for {request.url}")

        return response

    def process_exception(self, request, exception):
        """Handle request exceptions."""
        retry_count = request.meta.get('retry_count', 0)

        if retry_count < self.max_retries:
            logger.warning(
                f"Retrying {request.url} (attempt {retry_count + 1}/{self.max_retries}) "
                f"due to exception: {exception}"
            )
            delay = self.retry_delay * (2 ** retry_count)
            time.sleep(delay)

            retry_request = request.copy()
            retry_request.meta['retry_count'] = retry_count + 1
            retry_request.dont_filter = True
            return retry_request

        logger.error(f"Max retries reached for {request.url} after exception: {exception}")
