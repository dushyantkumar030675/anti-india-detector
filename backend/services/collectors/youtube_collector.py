"""
YouTube Data Collector
Searches for anti-India content using YouTube Data API v3.
Runs on a scheduled polling loop.
"""
import asyncio
import json
import structlog
import httpx
import redis.asyncio as aioredis
from datetime import datetime, timedelta
from config.settings import get_settings

log = structlog.get_logger()
settings = get_settings()

SEARCH_QUERIES = [
    "india terrorist attack",
    "modi genocide",
    "hindu nationalist violence",
    "india war crimes",
    "boycott india products",
]

STREAM_NAME = "content:raw"
POLL_INTERVAL_SECS = 900  # 15 minutes


async def fetch_youtube_results(query: str, published_after: str) -> list[dict]:
    if not settings.youtube_api_key:
        return []

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "publishedAfter": published_after,
        "maxResults": 50,
        "order": "date",
        "key": settings.youtube_api_key,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])


async def collect_youtube(redis_client: aioredis.Redis):
    published_after = (datetime.utcnow() - timedelta(hours=1)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    for query in SEARCH_QUERIES:
        try:
            items = await fetch_youtube_results(query, published_after)
            for item in items:
                snippet = item.get("snippet", {})
                video_id = item["id"].get("videoId", "")
                payload = {
                    "source": "youtube",
                    "content_id": f"yt:{video_id}",
                    "text": f"{snippet.get('title', '')} {snippet.get('description', '')}",
                    "author_id": snippet.get("channelId", ""),
                    "author_username": snippet.get("channelTitle", ""),
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "collected_at": snippet.get("publishedAt"),
                }
                await redis_client.xadd(STREAM_NAME, {"data": json.dumps(payload)})
            log.info("YouTube results enqueued", query=query, count=len(items))
        except Exception as e:
            log.error("YouTube collection failed", query=query, error=str(e))


async def run_youtube_collector():
    redis_client = await aioredis.from_url(settings.redis_url)
    while True:
        log.info("YouTube collection cycle starting")
        await collect_youtube(redis_client)
        await asyncio.sleep(POLL_INTERVAL_SECS)


if __name__ == "__main__":
    asyncio.run(run_youtube_collector())
