"""
Bot Detection & Coordination Analysis Service
Uses behavioral signals to estimate bot probability and detect coordinated campaigns.
"""
from __future__ import annotations
import hashlib
import math
import structlog
import redis.asyncio as aioredis
from config.settings import get_settings

log = structlog.get_logger()
settings = get_settings()


# ── Bot detection heuristics ────────────────────────────────────────────────
def estimate_bot_probability(author_meta: dict) -> float:
    """
    Estimate bot probability from account metadata (0.0–1.0).
    author_meta keys: followers, following, tweets_count, account_age_days,
                      has_profile_pic, has_description, verified
    """
    score = 0.0
    weights = []

    # New account with high activity
    age = author_meta.get("account_age_days", 365)
    tweets = author_meta.get("tweets_count", 0)
    if age > 0:
        tweets_per_day = tweets / age
        if tweets_per_day > 50:
            score += 0.3
        elif tweets_per_day > 20:
            score += 0.15

    # Unusual follower/following ratio
    followers = author_meta.get("followers", 1)
    following = author_meta.get("following", 1)
    ratio = following / max(followers, 1)
    if ratio > 10:
        score += 0.25
    elif ratio > 5:
        score += 0.10

    # Missing profile info
    if not author_meta.get("has_profile_pic"):
        score += 0.15
    if not author_meta.get("has_description"):
        score += 0.10

    # Very new account
    if age < 30:
        score += 0.20
    elif age < 90:
        score += 0.10

    # Verified accounts are very unlikely bots
    if author_meta.get("verified"):
        score -= 0.40

    return max(0.0, min(1.0, score))


# ── Coordination detection ──────────────────────────────────────────────────
async def check_coordination(
    text: str,
    author_id: str,
    redis_client: aioredis.Redis,
) -> dict:
    """
    Detect if this content is part of a coordinated campaign.
    Uses Redis to track content fingerprints and author posting patterns.
    """
    result = {
        "is_coordinated": False,
        "coordination_cluster": None,
        "coordination_score": 0.0,
    }

    # Content fingerprint (near-duplicate detection)
    words = text.lower().split()
    if len(words) > 5:
        sample = " ".join(sorted(words[:20]))
        fingerprint = hashlib.md5(sample.encode()).hexdigest()[:16]
        fp_key = f"fp:{fingerprint}"

        count = await redis_client.incr(fp_key)
        await redis_client.expire(fp_key, 3600)  # 1 hour window

        if count >= 5:  # same content posted 5+ times in 1hr
            result["is_coordinated"] = True
            result["coordination_cluster"] = fingerprint
            result["coordination_score"] = min(count / 20, 1.0)

    # Author posting velocity (too fast = bot/coordinated)
    velocity_key = f"velocity:{author_id}"
    post_count = await redis_client.incr(velocity_key)
    await redis_client.expire(velocity_key, 3600)

    if post_count > 30:
        result["is_coordinated"] = True
        result["coordination_score"] = max(result["coordination_score"], 0.85)

    return result


# ── Reach scoring ────────────────────────────────────────────────────────────
def calculate_reach_score(likes: int, shares: int, views: int) -> int:
    """Logarithmic reach score 0–100."""
    raw = likes * 1 + shares * 3 + views * 0.01
    if raw <= 0:
        return 0
    return min(int(math.log10(raw + 1) * 25), 100)
