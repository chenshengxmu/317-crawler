"""
Sina News Spider (新浪新闻)
Crawls news articles from https://news.sina.com.cn/
"""

from datetime import datetime
from crawler.items import NewsArticle
from crawler.spiders.base_spider import BaseNewsSpider
from processing import text_processor, deduplicator
from loguru import logger


class SinaSpider(BaseNewsSpider):
    """Spider for Sina News."""

    name = 'sina'
    allowed_domains = ['sina.com.cn']

    start_urls = [
        'https://news.sina.com.cn/',
        'https://news.sina.com.cn/china/',
        'https://news.sina.com.cn/world/',
    ]

    category_map = {
        '/c/': '国内',
        '/china/': '国内',
        '/world/': '国际',
        '/finance/': '财经',
        '/tech/': '科技',
        '/o/': '社会',
        '/s/': '体育',
    }

    def parse(self, response):
        """Parse section pages and extract article links."""
        category = self._get_category_from_url(response.url)

        # Sina desktop article URLs contain /doc- pattern
        links = response.css('a::attr(href)').getall()
        article_urls = set()
        for url in links:
            if url and '/doc-' in url and 'sina.com.cn' in url and url.startswith('http'):
                article_urls.add(url)
            elif url and '/doc-' in url and url.startswith('//'):
                article_urls.add('https:' + url)

        logger.info(f"Found {len(article_urls)} article links on {response.url}")

        for url in article_urls:
            yield self.make_request(
                url,
                callback=self.parse_article,
                meta={'category': category}
            )

    def parse_article(self, response):
        """Parse individual Sina article page."""
        try:
            title = self._extract_title(response)
            content = self._extract_content(response)
            publish_time = self._extract_publish_time(response)
            author = self._extract_author(response)
            images = self.extract_images(
                response,
                '#article img::attr(src), #artibody img::attr(src)'
            )

            if not title or not content:
                logger.warning(f"Missing title or content: {response.url}")
                return

            cleaned_content = text_processor.clean_article_text(content)

            if not text_processor.is_valid_article(cleaned_content, min_length=100):
                logger.warning(f"Article too short: {response.url}")
                return

            summary = text_processor.extract_summary(cleaned_content, max_length=200)
            url_hash = deduplicator.generate_url_hash(response.url)
            content_hash = deduplicator.generate_content_hash(cleaned_content)
            category = response.meta.get('category', '其他')

            article = NewsArticle()
            article['title'] = title
            article['content'] = cleaned_content
            article['summary'] = summary
            article['source'] = 'sina'
            article['category'] = category
            article['author'] = author or '新浪新闻'
            article['tags'] = []
            article['url'] = response.url
            article['images'] = images
            article['publish_time'] = publish_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            article['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            article['url_hash'] = url_hash
            article['content_hash'] = content_hash

            logger.info(f"Scraped: {title[:60]}")
            yield article

        except Exception as e:
            logger.error(f"Failed to parse {response.url}: {e}")

    def _extract_title(self, response) -> str:
        """Extract article title — try multiple selectors."""
        for selector in [
            'meta[property="og:title"]::attr(content)',
            'h1#artibodyTitle::text',
            'h1.main-title::text',
            'h1.article-title::text',
        ]:
            val = response.css(selector).get()
            if val:
                cleaned = self.clean_text(val)
                if cleaned and cleaned != '新闻中心':
                    return cleaned
        # Fallback: second h1 (first is often site header)
        all_h1 = response.css('h1::text').getall()
        for h1 in all_h1:
            cleaned = self.clean_text(h1)
            if cleaned and cleaned != '新闻中心' and len(cleaned) > 5:
                return cleaned
        return ""

    def _extract_content(self, response) -> str:
        """Extract article body text."""
        for selector in ['#article', '#artibody', '.article-content', '.article', 'article']:
            paragraphs = response.css(f'{selector} p::text').getall()
            if paragraphs:
                return self.clean_text('\n'.join(p for p in paragraphs if p.strip()))
        return ""

    def _extract_publish_time(self, response) -> str:
        """Extract publish time."""
        for selector in [
            'meta[property="article:published_time"]::attr(content)',
            '.date::text',
            '.time-source span::text',
            '.article-time::text',
            'span.date::text',
        ]:
            date_str = response.css(selector).get()
            if date_str:
                parsed = self.parse_chinese_date(date_str.strip())
                if parsed:
                    return parsed
        return None

    def _extract_author(self, response) -> str:
        """Extract author/source."""
        for selector in [
            'meta[name="author"]::attr(content)',
            '.source a::text',
            '.source::text',
            '.article-source::text',
        ]:
            val = response.css(selector).get()
            if val:
                return self.clean_text(val)
        return ""

    def _get_category_from_url(self, url: str) -> str:
        """Determine category from URL path."""
        for key, value in self.category_map.items():
            if key in url:
                return value
        return '其他'
