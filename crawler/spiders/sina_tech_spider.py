"""
Sina Tech News Spider (新浪科技新闻)
使用 Sina 滚动 API (lid=2515) 抓取过去一个月的科技新闻。
API 每页50条，约35页覆盖一个月数据。
"""

import time
import json
from datetime import datetime
from urllib.parse import urlencode

import scrapy
from crawler.items import NewsArticle
from crawler.spiders.base_spider import BaseNewsSpider
from processing import text_processor, deduplicator
from loguru import logger


class SinaTechSpider(BaseNewsSpider):
    """抓取新浪科技频道过去一个月的新闻。"""

    name = 'sina_tech'
    allowed_domains = ['sina.com.cn', 'feed.mix.sina.com.cn']

    # Sina 滚动 API — lid=2515 是科技频道，pageid=153
    API_BASE = 'https://feed.mix.sina.com.cn/api/roll/get'
    API_LID = '2515'
    API_PAGEID = '153'
    API_PAGE_SIZE = 50

    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'DOWNLOAD_DELAY': 0.3,
        'ROBOTSTXT_OBEY': False,   # API endpoint, no robots.txt
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 3.0,
    }

    def __init__(self, days=30, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.days = int(days)
        self.cutoff_ts = time.time() - self.days * 86400
        self.cutoff_date = datetime.fromtimestamp(self.cutoff_ts).strftime('%Y-%m-%d')
        logger.info(f"SinaTechSpider: 抓取 {self.days} 天内科技新闻 (>= {self.cutoff_date})")

    def start_requests(self):
        """从第1页开始请求滚动 API。"""
        yield self._api_request(page=1)

    def _api_request(self, page: int):
        """构造 API 请求。"""
        params = {
            'pageid': self.API_PAGEID,
            'lid': self.API_LID,
            'num': self.API_PAGE_SIZE,
            'page': page,
            'encode': 'utf-8',
        }
        url = f"{self.API_BASE}?{urlencode(params)}"
        return scrapy.Request(
            url=url,
            callback=self.parse_api,
            headers=self.get_headers(),
            meta={'page': page, 'handle_httpstatus_all': True},
            errback=self.handle_error,
        )

    def parse_api(self, response):
        """解析 API 响应，提取文章 URL，并请求下一页。"""
        page = response.meta['page']
        try:
            data = json.loads(response.text)
            items = data.get('result', {}).get('data', [])
        except Exception as e:
            logger.error(f"API 解析失败 page={page}: {e}")
            return

        if not items:
            logger.info(f"API 第 {page} 页为空，停止翻页")
            return

        # 过滤出在时间范围内的文章
        in_range = [i for i in items if float(i.get('ctime', 0)) > self.cutoff_ts]
        oldest_ts = min(float(i.get('ctime', 0)) for i in items)
        oldest_date = datetime.fromtimestamp(oldest_ts).strftime('%Y-%m-%d')

        logger.info(
            f"API page={page}: {len(items)} 条, {len(in_range)} 条在范围内, "
            f"最早={oldest_date}"
        )

        # 请求每篇文章
        for item in in_range:
            url = item.get('url', '').strip()
            if not url or 'sina.com.cn' not in url:
                continue
            # 从 API 元数据中提取已知字段，减少解析工作
            meta = {
                'api_title': item.get('title', '').strip(),
                'api_ctime': item.get('ctime', ''),
                'api_intro': item.get('intro', '').strip(),
                'category': '科技',
            }
            yield self.make_request(url, callback=self.parse_article, meta=meta)

        # 如果本页最早文章还在范围内，继续翻页
        if oldest_ts > self.cutoff_ts and len(items) == self.API_PAGE_SIZE:
            yield self._api_request(page + 1)

    def parse_article(self, response):
        """解析文章页面。"""
        try:
            # 优先用 API 提供的标题，fallback 到页面解析
            title = response.meta.get('api_title') or self._extract_title(response)
            if not title:
                return

            content = self._extract_content(response)
            if not content:
                logger.debug(f"无正文内容: {response.url}")
                return

            cleaned_content = text_processor.clean_article_text(content)
            if not text_processor.is_valid_article(cleaned_content, min_length=80):
                return

            # 发布时间：优先 API 时间戳
            ctime = response.meta.get('api_ctime')
            if ctime:
                publish_time = datetime.fromtimestamp(float(ctime)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                publish_time = self._extract_publish_time(response) or datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 摘要：优先 API intro
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
            article['source'] = 'sina'
            article['category'] = '科技'
            article['author'] = self._extract_author(response) or '新浪科技'
            article['tags'] = []
            article['url'] = response.url
            article['images'] = self.extract_images(response, '#article img::attr(src), #artibody img::attr(src)')
            article['publish_time'] = publish_time
            article['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            article['url_hash'] = url_hash
            article['content_hash'] = content_hash

            yield article

        except Exception as e:
            logger.error(f"解析文章失败 {response.url}: {e}")

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
