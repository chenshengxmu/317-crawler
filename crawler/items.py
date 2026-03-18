"""
Scrapy items for news articles.
Defines the data structure for crawled news articles.
"""

import scrapy
from datetime import datetime


class NewsArticle(scrapy.Item):
    """News article item."""

    # Article content
    title = scrapy.Field()
    content = scrapy.Field()
    summary = scrapy.Field()

    # Metadata
    source = scrapy.Field()
    category = scrapy.Field()
    author = scrapy.Field()
    tags = scrapy.Field()

    # URLs and images
    url = scrapy.Field()
    images = scrapy.Field()

    # Timestamps
    publish_time = scrapy.Field()
    crawl_time = scrapy.Field()

    # Deduplication
    url_hash = scrapy.Field()
    content_hash = scrapy.Field()
