"""
Base spider class with shared functionality for all news spiders.
Provides common utilities for Chinese news crawling.
"""

import re
from datetime import datetime
from typing import List, Optional
import scrapy
from fake_useragent import UserAgent
from loguru import logger


class BaseNewsSpider(scrapy.Spider):
    """Base spider with shared functionality."""

    # Default settings
    custom_settings = {
        'CONCURRENT_REQUESTS': 16,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'DOWNLOAD_DELAY': 0.5,
        'ROBOTSTXT_OBEY': True,
        'USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ua = UserAgent()

    def get_random_user_agent(self) -> str:
        """Get a random user agent."""
        try:
            return self.ua.random
        except Exception:
            return self.custom_settings['USER_AGENT']

    def get_headers(self) -> dict:
        """Get request headers with Chinese language support."""
        return {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

    def parse_chinese_date(self, date_str: str) -> Optional[str]:
        """
        Parse Chinese date strings to ISO format.

        Args:
            date_str: Date string in various formats

        Returns:
            ISO formatted date string (YYYY-MM-DD HH:MM:SS) or None
        """
        if not date_str:
            return None

        try:
            # Clean the date string
            date_str = date_str.strip()

            # Try common formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d %H:%M',
                '%Y/%m/%d',
                '%Y年%m月%d日 %H:%M:%S',
                '%Y年%m月%d日 %H:%M',
                '%Y年%m月%d日',
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue

            # Handle relative dates (今天, 昨天, etc.)
            now = datetime.now()

            if '今天' in date_str or '今日' in date_str:
                time_match = re.search(r'(\d{1,2}):(\d{2})', date_str)
                if time_match:
                    hour, minute = time_match.groups()
                    dt = now.replace(hour=int(hour), minute=int(minute), second=0)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')

            if '昨天' in date_str or '昨日' in date_str:
                time_match = re.search(r'(\d{1,2}):(\d{2})', date_str)
                if time_match:
                    hour, minute = time_match.groups()
                    dt = now.replace(hour=int(hour), minute=int(minute), second=0)
                    dt = dt.replace(day=dt.day - 1)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')

            # Handle "X分钟前", "X小时前"
            minutes_match = re.search(r'(\d+)\s*分钟前', date_str)
            if minutes_match:
                minutes = int(minutes_match.group(1))
                dt = now.replace(second=0, microsecond=0)
                dt = dt.replace(minute=dt.minute - minutes)
                return dt.strftime('%Y-%m-%d %H:%M:%S')

            hours_match = re.search(r'(\d+)\s*小时前', date_str)
            if hours_match:
                hours = int(hours_match.group(1))
                dt = now.replace(second=0, microsecond=0)
                dt = dt.replace(hour=dt.hour - hours)
                return dt.strftime('%Y-%m-%d %H:%M:%S')

            logger.warning(f"Could not parse date: {date_str}")
            return None

        except Exception as e:
            logger.error(f"Date parsing error: {e}")
            return None

    def extract_images(self, response, selector: str = 'img::attr(src)') -> List[str]:
        """
        Extract image URLs from response.

        Args:
            response: Scrapy response
            selector: CSS selector for images

        Returns:
            List of image URLs
        """
        try:
            images = response.css(selector).getall()
            # Filter and clean image URLs
            cleaned_images = []
            for img in images:
                if img and img.startswith('http'):
                    cleaned_images.append(img)
                elif img and img.startswith('//'):
                    cleaned_images.append('https:' + img)
                elif img and img.startswith('/'):
                    cleaned_images.append(response.urljoin(img))

            return cleaned_images[:10]  # Limit to 10 images

        except Exception as e:
            logger.error(f"Image extraction error: {e}")
            return []

    def clean_text(self, text) -> str:
        """
        Clean extracted text.

        Args:
            text: Raw text or list of text

        Returns:
            Cleaned text string
        """
        if isinstance(text, list):
            text = ' '.join(text)

        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def make_request(self, url: str, callback, **kwargs):
        """
        Make a request with proper headers and error handling.

        Args:
            url: URL to request
            callback: Callback function
            **kwargs: Additional request parameters

        Returns:
            Scrapy Request
        """
        return scrapy.Request(
            url=url,
            callback=callback,
            headers=self.get_headers(),
            errback=self.handle_error,
            dont_filter=False,
            **kwargs
        )

    def handle_error(self, failure):
        """Handle request errors."""
        logger.error(f"Request failed: {failure.request.url} - {failure.value}")
