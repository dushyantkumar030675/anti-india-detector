"""
Analysis Worker
Consumes raw content from Redis Streams, runs the full AI pipeline,
saves incidents to PostgreSQL, and dispatches alerts.
"""
import asyncio
import json
import uuid
import structlog
import redis.asyncio as aioredis
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config.settings import get_settings
from config.database import AsyncSessionLocal, init_db
from models.models import Incident, SeverityLevel, ContentSource
from services.analyzers.nlp_analyzer import analyze_text
from services.analyzers.coordination_analyzer import (
    estimate_bot_probability,
    check_coordination,
    calculate_reach_score,
)
from services.analyzers.scoring_engine import compute_threat_score
from services.alert_service import dispatch_alerts

log = structlog.get_logger()
settings = get_settings()

STREAM_NAME = "content:raw"
CONSUMER_GROUP = "analysis_workers"
CONSUMER_NAME = f"worker-{uuid.uuid4().hex[:8]}"


async def process_item(data: dict, redis_client: aioredis.Redis, db: AsyncSession):
    content_id = data.get("content_id", f"unknown:{uuid.uuid4().hex}")

    # Check for duplicate
    existing = await db.execute(
        select(Incident).where(Incident.content_id == content_id)
    )
    if existing.scalar_one_or_none():
        log.debug("Duplicate skipped", content_id=content_id)
        return

    text = data.get("text", "") or ""
    if not text.strip():
        return

    # ── NLP analysis ──────────────────────────────────────────────────────
    nlp = analyze_text(text)

    # ── Bot detection ─────────────────────────────────────────────────────
    author_meta = data.get("author_meta", {})
    bot_prob = estimate_bot_probability(author_meta)

    # ── Coordination detection ────────────────────────────────────────────
    coord = await check_coordination(text, data.get("author_id", ""), redis_client)

    # ── Reach scoring ─────────────────────────────────────────────────────
    metrics = data.get("public_metrics", {})
    reach = calculate_reach_score(
        likes=metrics.get("like_count", 0),
        shares=metrics.get("retweet_count", 0),
        views=metrics.get("impression_count", 0),
    )

    # ── Threat scoring ────────────────────────────────────────────────────
    score_result = compute_threat_score(
        keyword_score=nlp["keyword_score"],
        hate_confidence=nlp["hate_confidence"],
        hate_label=nlp["hate_label"],
        sentiment_score=nlp["sentiment_score"],
        bot_probability=bot_prob,
        coordination_score=coord["coordination_score"],
        reach_score=reach,
    )

    # ── Persist incident ──────────────────────────────────────────────────
    source_str = data.get("source", "manual")
    try:
        source = ContentSource(source_str)
    except ValueError:
        source = ContentSource.manual

    incident = Incident(
        content_id=content_id,
        source=source,
        url=data.get("url"),
        author_id=data.get("author_id"),
        author_username=data.get("author_username"),
        text=text[:4000],
        language=nlp["language"],
        threat_score=score_result["threat_score"],
        severity=SeverityLevel(score_result["severity"]),
        categories=nlp["categories"],
        sentiment=nlp["sentiment"],
        sentiment_score=nlp["sentiment_score"],
        entities=nlp["entities"],
        keywords=nlp["keywords"],
        is_coordinated=coord["is_coordinated"],
        bot_probability=bot_prob,
        coordination_cluster=coord.get("coordination_cluster"),
        reach_score=reach,
        recommended_action=score_result["recommended_action"],
        collected_at=datetime.fromisoformat(data["collected_at"]) if data.get("collected_at") else None,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    log.info(
        "Incident saved",
        content_id=content_id,
        threat_score=score_result["threat_score"],
        severity=score_result["severity"],
    )

    # ── Alert dispatch ────────────────────────────────────────────────────
    if score_result["threat_score"] >= settings.alert_threshold:
        await dispatch_alerts({
            **score_result,
            "source": source_str,
            "url": data.get("url"),
            "text": text,
            "categories": nlp["categories"],
            "language": nlp["language"],
            "is_coordinated": coord["is_coordinated"],
            "bot_probability": bot_prob,
        })


async def run_worker():
    await init_db()
    redis_client = await aioredis.from_url(settings.redis_url)

    # Ensure consumer group exists
    try:
        await redis_client.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
    except Exception:
        pass  # Group already exists

    log.info("Analysis worker started", consumer=CONSUMER_NAME)

    while True:
        try:
            messages = await redis_client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={STREAM_NAME: ">"},
                count=10,
                block=5000,
            )

            if not messages:
                continue

            async with AsyncSessionLocal() as db:
                for _, entries in messages:
                    for entry_id, fields in entries:
                        try:
                            data = json.loads(fields[b"data"] if b"data" in fields else fields["data"])
                            await process_item(data, redis_client, db)
                            await redis_client.xack(STREAM_NAME, CONSUMER_GROUP, entry_id)
                        except Exception as e:
                            log.error("Processing error", error=str(e), entry_id=entry_id)

        except Exception as e:
            log.error("Worker loop error", error=str(e))
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(run_worker())
