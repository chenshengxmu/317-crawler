"""
分两步抓取新浪科技新闻：
步骤1：用 requests 慢速翻页获取所有文章 URL（保存到文件）
步骤2：用 Scrapy 并发抓取文章正文并写入 ES

这样可以避免 Scrapy 并发时 API 翻页被限流。
"""

import sys
import time
import json
import requests
from pathlib import Path
from datetime import datetime
from loguru import logger

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

API_BASE = 'https://feed.mix.sina.com.cn/api/roll/get'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://tech.sina.com.cn/',
}

def fetch_all_tech_urls(days: int = 30, output_file: str = 'tech_urls.json') -> list:
    """
    翻页获取过去 N 天的科技新闻 URL 列表。
    返回 [{url, title, ctime, intro}, ...] 列表。
    """
    cutoff_ts = time.time() - days * 86400
    cutoff_date = datetime.fromtimestamp(cutoff_ts).strftime('%Y-%m-%d')
    logger.info(f"获取 {days} 天内科技新闻 URL (>= {cutoff_date})")

    all_items = []
    seen_urls = set()

    for page in range(1, 40):
        params = {
            'pageid': '153',
            'lid': '2515',
            'num': '50',
            'page': str(page),
            'encode': 'utf-8',
        }
        try:
            r = requests.get(API_BASE, params=params, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                logger.warning(f"Page {page}: HTTP {r.status_code}, 停止")
                break

            data = r.json()
            items = data.get('result', {}).get('data', [])
            if not items:
                logger.info(f"Page {page}: 空响应，停止")
                break

            in_range = [i for i in items if float(i.get('ctime', 0)) > cutoff_ts]
            oldest_ts = min(float(i.get('ctime', 0)) for i in items)
            oldest_date = datetime.fromtimestamp(oldest_ts).strftime('%Y-%m-%d')

            new_count = 0
            for item in in_range:
                url = item.get('url', '').strip()
                if url and url not in seen_urls and 'sina.com.cn' in url:
                    seen_urls.add(url)
                    all_items.append({
                        'url': url,
                        'title': item.get('title', '').strip(),
                        'ctime': item.get('ctime', ''),
                        'intro': item.get('intro', '').strip(),
                    })
                    new_count += 1

            logger.info(
                f"Page {page}: {len(in_range)}/{len(items)} in range, "
                f"新增 {new_count} 条, 最早={oldest_date}, 累计={len(all_items)}"
            )

            if oldest_ts < cutoff_ts:
                logger.info(f"已到达 {days} 天边界，停止翻页")
                break

        except Exception as e:
            logger.error(f"Page {page} 请求失败: {e}")
            time.sleep(3)
            continue

        # 每页间隔 1.5 秒，避免被限流
        time.sleep(1.5)

    # 保存到文件
    output_path = project_root / output_file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    logger.success(f"共获取 {len(all_items)} 条 URL，已保存到 {output_path}")
    return all_items


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=30)
    parser.add_argument('--output', type=str, default='tech_urls.json')
    args = parser.parse_args()
    fetch_all_tech_urls(days=args.days, output_file=args.output)
