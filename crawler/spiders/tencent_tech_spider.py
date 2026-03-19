"""
Tencent Tech Spider — 从预先获取的腾讯科技 URL 列表抓取文章正文。
配合 fetch_tencent_urls.py 使用，实现两阶段抓取。
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import scrapy
from crawler.items import NewsArticle
from crawler.spiders.base_spider import BaseNewsSpider
from processing import text_processor, deduplicator
from loguru import logger


class TencentTechSpider(BaseNewsSpider):
    """从腾讯科技 JSON URL 列表文件批量抓取文章正文。"""

    name = 'tencent_tech'
    allowed_domains = ['news.qq.com', 'qq.com']

    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'DOWNLOAD_DELAY': 0.3,
        'ROBOTSTXT_OBEY': False,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 4.0,
    }

    def __init__(self, url_file='tencent_urls.json', category='科技', source='tencent', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url_file = Path(__file__).parent.parent.parent / url_file
        self.category = category
        self.source = source

    def start_requests(self):
        """从 JSON 文件读取 URL 列表并生成请求。"""
        if not self.url_file.exists():
            logger.error(f"URL 文件不存在: {self.url_file}")
            return

        with open(self.url_file, 'r', encoding='utf-8') as f:
            url_items = json.load(f)

        logger.info(f"从 {self.url_file} 读取 {len(url_items)} 条 URL")

        for item in url_items:
            url = item.get('url', '').strip()
            if not url:
                continue
            meta = {
                'api_title': item.get('title', ''),
                'api_ctime': item.get('ctime', ''),
                'api_intro': item.get('intro', ''),
                'category': self.category,
            }
            yield self.make_request(url, callback=self.parse_article, meta=meta)

    def parse_article(self, response):
        """解析文章页面。"""
        try:
            title = response.meta.get('api_title') or self._extract_title(response)
            if not title:
                return

            content = self._extract_content(response)
            if not content:
                return

            cleaned_content = text_processor.clean_article_text(content)
            if not text_processor.is_valid_article(cleaned_content, min_length=80):
                return

            ctime = response.meta.get('api_ctime')
            if ctime:
                publish_time = datetime.fromtimestamp(float(ctime)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                publish_time = self._extract_publish_time(response) or datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            api_intro = response.meta.get('api_intro', '')
            if api_intro and len(api_intro) >= 20:
                summary = text_processor.clean_article_text(api_intro, remove_urls_flag=False)
            else:
                summary = text_processor.extract_summary(cleaned_content, max_length=200)

            url_hash = deduplicator.generate_url_hash(response.url)
            content_hash = deduplicator.generate_content_hash(cleaned_content)

            article = NewsArticle()
            article['title'] = title
            article['content'] = cleaned_content
            article['summary'] = summary
            article['source'] = self.source
            article['category'] = self.category
            article['author'] = self._extract_author(response) or '腾讯科技'
            article['tags'] = []
            article['url'] = response.url
            article['images'] = self.extract_images(
                response, 'div.rich_media_content img::attr(src)'
            )
            article['publish_time'] = publish_time
            article['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            article['url_hash'] = url_hash
            article['content_hash'] = content_hash

            logger.info(f"✓ {title[:50]}")
            yield article

        except Exception as e:
            logger.error(f"解析失败 {response.url}: {e}")

    def _extract_title(self, response) -> str:
        # og:title meta tag (most reliable)
        val = response.css('meta[property="og:title"]::attr(content)').get()
        if val:
            t = self.clean_text(val)
            if t and t not in ('腾讯新闻', '腾讯科技', '科技'):
                return t

        # Try window.DATA JS object
        js_text = ' '.join(response.css('script::text').getall())
        m = re.search(r'"title"\s*:\s*"([^"]{5,})"', js_text)
        if m:
            return self.clean_text(m.group(1))

        # Fallback to h1
        for h1 in response.css('h1::text').getall():
            t = self.clean_text(h1)
            if t and len(t) > 5 and t not in ('腾讯新闻', '腾讯科技'):
                return t

        return ''

    def _extract_content(self, response) -> str:
        for sel in [
            'div.rich_media_content',
            'div#artibody',
            'div.article-content',
            'div[class*="article"]',
        ]:
            paras = response.css(f'{sel} p::text').getall()
            if paras:
                return self.clean_text('\n'.join(p for p in paras if p.strip()))
        return ''

    def _extract_publish_time(self, response) -> str:
        # article:published_time meta (ISO 8601)
        val = response.css('meta[property="article:published_time"]::attr(content)').get()
        if val:
            # Strip timezone offset e.g. "+08:00"
            val = re.sub(r'\+\d{2}:\d{2}$', '', val.strip()).replace('T', ' ')
            parsed = self.parse_chinese_date(val)
            if parsed:
                return parsed

        # Regex in page text: "2026-03-19 10:30 发布于"
        page_text = response.text
        m = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*发布于', page_text)
        if m:
            parsed = self.parse_chinese_date(m.group(1))
            if parsed:
                return parsed

        # window.DATA JS: "pubtime":"2026-03-19 10:30:00"
        js_text = ' '.join(response.css('script::text').getall())
        m = re.search(r'"pubtime"\s*:\s*"([^"]+)"', js_text)
        if m:
            parsed = self.parse_chinese_date(m.group(1))
            if parsed:
                return parsed

        return ''

    def _extract_author(self, response) -> str:
        # window.DATA JS: "media":"腾讯科技"
        js_text = ' '.join(response.css('script::text').getall())
        m = re.search(r'"media"\s*:\s*"([^"]{2,30})"', js_text)
        if m:
            author = self.clean_text(m.group(1))
            if author:
                return author

        # meta[name="author"]
        val = response.css('meta[name="author"]::attr(content)').get()
        if val:
            return self.clean_text(val)

        # CSS selectors for author display
        for sel in ['.article-author__name::text', '.source::text']:
            val = response.css(sel).get()
            if val:
                return self.clean_text(val)

        return ''
