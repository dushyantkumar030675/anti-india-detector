"""
Twitter / X Data Collector
Streams tweets mentioning anti-India keywords using Twitter API v2.
"""
import asyncio
import json
import structlog
import tweepy
import redis.asyncio as aioredis
from config.settings import get_settings

log = structlog.get_logger()
settings = get_settings()

TRACK_KEYWORDS = [
    "india terrorist", "modi fascist", "hindu extremist",
    "india genocide", "boycott india", "bharat murdabad",
    "india war criminal", "down with india", "india occupier",
]

STREAM_NAME = "content:raw"


class TwitterCollector(tweepy.StreamingClient):
    def __init__(self, bearer_token: str, redis_client: aioredis.Redis):
        super().__init__(bearer_token, wait_on_rate_limit=True)
        self.redis = redis_client

    def on_tweet(self, tweet):
        asyncio.create_task(self._enqueue(tweet))

    async def _enqueue(self, tweet):
        payload = {
            "source": "twitter",
            "content_id": f"tw:{tweet.id}",
            "text": tweet.text,
            "author_id": str(tweet.author_id),
            "url": f"https://twitter.com/i/web/status/{tweet.id}",
            "collected_at": tweet.created_at.isoformat() if tweet.created_at else None,
            "public_metrics": tweet.public_metrics or {},
        }
        await self.redis.xadd(STREAM_NAME, {"data": json.dumps(payload)})
        log.info("Tweet enqueued", tweet_id=tweet.id)

    def on_error(self, status):
        log.error("Twitter stream error", status=status)


async def start_twitter_stream(redis_url: str):
    if not settings.twitter_bearer_token:
        log.warning("Twitter bearer token not set, skipping collector")
        return

    redis_client = await aioredis.from_url(redis_url)
    collector = TwitterCollector(settings.twitter_bearer_token, redis_client)

    # Add filter rules
    existing = collector.get_rules()
    if existing.data:
        ids = [r.id for r in existing.data]
        collector.delete_rules(ids)

    rules = [tweepy.StreamRule(f'"{kw}"') for kw in TRACK_KEYWORDS[:5]]
    collector.add_rules(rules)

    log.info("Starting Twitter stream", keywords=TRACK_KEYWORDS[:5])
    collector.filter(tweet_fields=["created_at", "author_id", "public_metrics"])


if __name__ == "__main__":
    asyncio.run(start_twitter_stream(settings.redis_url))
