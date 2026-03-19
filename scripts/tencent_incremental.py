"""
腾讯科技增量抓取脚本 — 每次只取第 1 页（约 20 条最新文章），
通过 Scrapy + 现有 pipeline 写入 ES，pipeline 内置 url_hash 去重，
已抓过的文章自动跳过。

用法：
    python scripts/tencent_incremental.py          # 默认取 1 页
    python scripts/tencent_incremental.py --pages 3  # 取前 3 页（约 60 条）

定时任务（crontab -e）：
    */5 * * * * /Users/chensheng/317/crawler/venv/bin/python \
        /Users/chensheng/317/crawler/scripts/tencent_incremental.py \
        >> /Users/chensheng/317/crawler/logs/tencent_incremental.log 2>&1
"""

import sys
import uuid
import json
import time
import argparse
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
_SKIP_TYPES = {'525'}


def fetch_latest_urls(pages: int = 1) -> list:
    """从 getPCList API 取前 N 页最新文章，返回 [{url, title, ctime, intro}, ...]。"""
    device_id = uuid.uuid4().hex + uuid.uuid4().hex[:4]
    results = []
    seen_ids = set()

    for page in range(1, pages + 1):
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
            r.raise_for_status()
            data = r.json()
            if data.get('code') != 0:
                logger.warning(f"API code={data.get('code')}, 停止")
                break

            raw = data.get('data') or []
            articles = []
            for item in raw:
                if item.get('articletype') in _SKIP_TYPES:
                    articles.extend(item.get('sub_item') or [])
                else:
                    articles.append(item)

            for a in articles:
                article_id = a.get('id', '').strip()
                pt = a.get('publish_time', '')
                if not article_id or not pt or article_id in seen_ids:
                    continue
                seen_ids.add(article_id)
                try:
                    ctime = str(int(datetime.strptime(pt, '%Y-%m-%d %H:%M:%S').timestamp()))
                except ValueError:
                    ctime = ''
                results.append({
                    'url': f'https://news.qq.com/rain/a/{article_id}',
                    'title': a.get('title', '').strip(),
                    'ctime': ctime,
                    'intro': a.get('abstract', a.get('intro', '')).strip(),
                })

        except Exception as e:
            logger.error(f"API 请求失败 (page={page}): {e}")

        if page < pages:
            time.sleep(0.3)

    return results


def run_scrapy(url_items: list) -> int:
    """用 Scrapy CrawlerProcess 抓取文章正文并写入 ES，返回成功入库数量。"""
    import tempfile
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings

    # 写临时 URL 文件供 spider 读取
    tmp = tempfile.NamedTemporaryFile(
        mode='w', suffix='.json', delete=False,
        dir=project_root, encoding='utf-8'
    )
    json.dump(url_items, tmp, ensure_ascii=False)
    tmp.close()
    tmp_path = Path(tmp.name)

    try:
        settings = get_project_settings()
        settings.set('LOG_ENABLED', False)   # 避免 Scrapy 日志与 loguru 混输

        process = CrawlerProcess(settings)
        process.crawl(
            'tencent_tech',
            url_file=str(tmp_path.relative_to(project_root)),
        )
        process.start()
    finally:
        tmp_path.unlink(missing_ok=True)

    # 从 pipeline 统计中读取结果（Scrapy stats 在 process 结束后可查）
    # 这里用 ES count 做粗略验证，返回 0 表示"无法精确统计"
    return 0


def main():
    parser = argparse.ArgumentParser(description='腾讯科技增量抓取')
    parser.add_argument('--pages', type=int, default=1,
                        help='每次取前 N 页（每页约 20 条），默认 1')
    args = parser.parse_args()

    start = datetime.now()
    logger.info(f"[{start:%Y-%m-%d %H:%M:%S}] 开始增量抓取（pages={args.pages}）")

    url_items = fetch_latest_urls(pages=args.pages)
    if not url_items:
        logger.warning("未获取到任何 URL，退出")
        return

    logger.info(f"获取到 {len(url_items)} 条候选 URL，启动 Scrapy...")
    run_scrapy(url_items)

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"增量抓取完成，耗时 {elapsed:.1f}s")


if __name__ == '__main__':
    main()
