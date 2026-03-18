"""
Scrapy settings for news crawler project.
"""

BOT_NAME = 'news_crawler'

SPIDER_MODULES = ['crawler.spiders']
NEWSPIDER_MODULE = 'crawler.spiders'

# Crawl responsibly
ROBOTSTXT_OBEY = True
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Concurrent requests
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 2
CONCURRENT_REQUESTS_PER_IP = 0

# Download delay (politeness)
DOWNLOAD_DELAY = 0.5
DOWNLOAD_TIMEOUT = 30

# HTTP cache (development only)
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Redirect settings
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 3

# Cookie settings
COOKIES_ENABLED = True

# Telnet Console (disabled for security)
TELNETCONSOLE_ENABLED = False

# Override the default request headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
}

# Spider middlewares — use Scrapy defaults (paths changed in 2.14)

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    'crawler.middlewares.RotateUserAgentMiddleware': 400,
    'crawler.middlewares.RateLimitMiddleware': 500,
    'crawler.middlewares.RetryMiddleware': 550,
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,  # Disable default
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': None,  # Disable default
}

# Configure item pipelines (order matters!)
ITEM_PIPELINES = {
    'crawler.pipelines.ValidationPipeline': 100,
    'crawler.pipelines.TextCleaningPipeline': 200,
    'crawler.pipelines.DeduplicationPipeline': 300,
    'crawler.pipelines.ElasticsearchPipeline': 400,
    'crawler.pipelines.StatsPipeline': 500,
}

# AutoThrottle settings (adaptive crawling)
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0
AUTOTHROTTLE_DEBUG = False

# Memory usage limits
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 512
MEMUSAGE_WARNING_MB = 256

# Logging
LOG_LEVEL = 'INFO'
LOG_ENCODING = 'utf-8'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'

# Feed exports (for testing)
FEED_EXPORT_ENCODING = 'utf-8'

# DNS timeout
DNS_TIMEOUT = 10

# Request fingerprinter
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'

# Twisted reactor
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
