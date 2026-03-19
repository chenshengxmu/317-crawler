"""
分两步抓取腾讯科技新闻：
步骤1：用 requests 翻页获取所有文章 URL（保存到文件）
步骤2：用 Scrapy 并发抓取文章正文并写入 ES

使用 POST /web_feed/getPCList API，无需登录，每页 20 条，
通过 flush_num 翻页，最多覆盖近 30 天内容。
"""

import sys
import uuid
import time
import json
import requests
from pathlib import Path
from datetime import datetime
from loguru import logger

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

PCLIST_API = 'https://i.news.qq.com/web_feed/getPCList'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://news.qq.com/ch/tech/',
    'Content-Type': 'application/json',
}

# 文章类型 525 = 热点精选聚合卡片（无独立 URL），跳过
_SKIP_TYPES = {'525'}


def fetch_all_tencent_urls(days: int = 30, output_file: str = 'tencent_urls.json') -> list:
    """
    翻页获取过去 N 天的腾讯科技新闻 URL 列表。
    返回 [{url, title, ctime, intro}, ...] 列表。
    """
    cutoff_ts = time.time() - days * 86400
    cutoff_date = datetime.fromtimestamp(cutoff_ts).strftime('%Y-%m-%d')
    logger.info(f"获取 {days} 天内腾讯科技新闻 URL (>= {cutoff_date})")

    # 每次运行生成一个固定的设备 ID（模拟同一浏览器）
    device_id = uuid.uuid4().hex + uuid.uuid4().hex[:4]

    all_items = []
    seen_ids = set()
    no_new_streak = 0

    for page in range(1, 200):
        payload = {
            'base_req': {'from': 'pc'},
            'forward': '2',
            'qimei36': device_id,
            'device_id': device_id,
            'flush_num': page,
            'channel_id': 'news_news_tech',
            'item_count': 20,
            'is_local_chlid': 'no',
        }
        try:
            r = requests.post(PCLIST_API, json=payload, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                logger.warning(f"Page {page}: HTTP {r.status_code}, 停止")
                break

            data = r.json()
            if data.get('code') != 0:
                logger.warning(f"Page {page}: code={data.get('code')}, 停止")
                break

            raw_items = data.get('data') or []
            # 过滤聚合卡片；展开 sub_item（如有）
            articles = []
            for item in raw_items:
                if item.get('articletype') in _SKIP_TYPES:
                    sub = item.get('sub_item') or []
                    articles.extend(sub)
                else:
                    articles.append(item)

            articles = [a for a in articles if a.get('publish_time')]

            in_range = []
            oldest_time = None
            for a in articles:
                pt = a.get('publish_time', '')
                if not pt:
                    continue
                try:
                    ts = datetime.strptime(pt, '%Y-%m-%d %H:%M:%S').timestamp()
                except ValueError:
                    continue
                if oldest_time is None or pt < oldest_time:
                    oldest_time = pt
                if ts > cutoff_ts:
                    in_range.append(a)

            new_count = 0
            for a in in_range:
                article_id = a.get('id', '').strip()
                if not article_id or article_id in seen_ids:
                    continue
                seen_ids.add(article_id)
                url = f'https://news.qq.com/rain/a/{article_id}'
                pt = a.get('publish_time', '')
                try:
                    ctime = str(int(datetime.strptime(pt, '%Y-%m-%d %H:%M:%S').timestamp()))
                except ValueError:
                    ctime = ''
                all_items.append({
                    'url': url,
                    'title': a.get('title', '').strip(),
                    'ctime': ctime,
                    'intro': a.get('abstract', a.get('intro', '')).strip(),
                })
                new_count += 1

            logger.info(
                f"Page {page}: {len(in_range)}/{len(articles)} in range, "
                f"新增 {new_count} 条, 最早={oldest_time}, 累计={len(all_items)}"
            )

            # 如果最早文章已超出时间窗口，停止
            if oldest_time and datetime.strptime(oldest_time, '%Y-%m-%d %H:%M:%S').timestamp() < cutoff_ts:
                logger.info(f"已到达 {days} 天边界，停止翻页")
                break

            # 连续 5 页无新内容则停止（API 已到底）
            if new_count == 0:
                no_new_streak += 1
                if no_new_streak >= 5:
                    logger.info("连续 5 页无新内容，停止翻页")
                    break
            else:
                no_new_streak = 0

        except Exception as e:
            logger.error(f"Page {page} 请求失败: {e}")
            time.sleep(3)
            continue

        time.sleep(0.5)

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
    parser.add_argument('--output', type=str, default='tencent_urls.json')
    args = parser.parse_args()
    fetch_all_tencent_urls(days=args.days, output_file=args.output)
