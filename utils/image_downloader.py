"""后台图片下载 worker"""
import asyncio
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

IMAGES_BASE = Path(__file__).parent.parent / "data" / "images"
INTERVAL = 10


def _ext_from_url(url: str) -> str:
    m = re.search(r'\.(\w{3,4})(?:\?|$)', url)
    return m.group(1) if m else 'jpg'


async def _download_one(client, url: str, save_path: Path) -> bool:
    try:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        resp = await client.get(url, timeout=30)
        if resp.status_code == 200:
            save_path.write_bytes(resp.content)
            return True
    except Exception as e:
        logger.debug("Image download failed: %s — %s", url, e)
    return False


async def run_image_downloader(stop_event: asyncio.Event):
    from utils import rss_store

    rss_store.init_image_queue_table()
    logger.info("Image downloader started")

    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        while not stop_event.is_set():
            pending = rss_store.get_pending_images(limit=5)
            if not pending:
                await asyncio.sleep(INTERVAL)
                continue

            by_article = {}
            for item in pending:
                by_article.setdefault(item["article_id"], []).append(item)

            for article_id, items in by_article.items():
                mapping = {}
                for item in items:
                    fname = f"img_{item['id']}.{_ext_from_url(item['image_url'])}"
                    local = IMAGES_BASE / str(article_id) / fname
                    ok = await _download_one(client, item["image_url"], local)
                    if ok:
                        rss_store.mark_image_done(item["id"], fname)
                        mapping[item["image_url"]] = fname
                    else:
                        rss_store.mark_image_failed(item["id"])

                if mapping:
                    rss_store.replace_article_images(article_id, mapping)

            await asyncio.sleep(2)

    logger.info("Image downloader stopped")
