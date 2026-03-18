"""
URL List Spider — 从预先获取的 URL 列表抓取文章正文。
配合 fetch_tech_urls.py 使用，实现两阶段抓取。
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import scrapy
from crawler.items import NewsArticle
from crawler.spiders.base_spider import BaseNewsSpider
from processing import text_processor, deduplicator
from loguru import logger


class UrlListSpider(BaseNewsSpider):
    """从 JSON URL 列表文件批量抓取文章正文。"""

    name = 'url_list'
    allowed_domains = ['sina.com.cn']

    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'DOWNLOAD_DELAY': 0.3,
        'ROBOTSTXT_OBEY': False,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 4.0,
    }

    def __init__(self, url_file='tech_urls.json', category='科技', source='sina', *args, **kwargs):
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
            article['author'] = self._extract_author(response) or '新浪科技'
            article['tags'] = []
            article['url'] = response.url
            article['images'] = self.extract_images(
                response, '#article img::attr(src), #artibody img::attr(src)'
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
        for sel in [
            'meta[property="og:title"]::attr(content)',
            'h1#artibodyTitle::text',
            'h1.main-title::text',
        ]:
            val = response.css(sel).get()
            if val:
                t = self.clean_text(val)
                if t and t not in ('新闻中心', '新浪科技', '科技'):
                    return t
        for h1 in response.css('h1::text').getall():
            t = self.clean_text(h1)
            if t and len(t) > 5 and t not in ('新闻中心', '新浪科技'):
                return t
        return ''

    def _extract_content(self, response) -> str:
        for sel in ['#article', '#artibody', '.article-content', '.article', 'article']:
            paras = response.css(f'{sel} p::text').getall()
            if paras:
                return self.clean_text('\n'.join(p for p in paras if p.strip()))
        return ''

    def _extract_publish_time(self, response) -> str:
        for sel in [
            'meta[property="article:published_time"]::attr(content)',
            '.date::text',
            '.time-source span::text',
            'span.date::text',
        ]:
            val = response.css(sel).get()
            if val:
                parsed = self.parse_chinese_date(val.strip())
                if parsed:
                    return parsed
        return ''

    def _extract_author(self, response) -> str:
        for sel in ['meta[name="author"]::attr(content)', '.source a::text', '.source::text']:
            val = response.css(sel).get()
            if val:
                return self.clean_text(val)
        return ''
