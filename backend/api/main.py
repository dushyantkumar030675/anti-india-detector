"""
Anti-India Campaign Detection API
FastAPI application exposing REST endpoints.
"""
import uuid
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, List
import structlog
import redis.asyncio as aioredis
from fastapi import FastAPI, Depends, HTTPException, Security, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from contextlib import asynccontextmanager

from config.settings import get_settings
from config.database import get_db, init_db
from models.models import Incident, SeverityLevel, ContentSource, ApiKey, TrendSnapshot
from services.analyzers.nlp_analyzer import analyze_text
from services.analyzers.coordination_analyzer import (
    estimate_bot_probability, check_coordination, calculate_reach_score
)
from services.analyzers.scoring_engine import compute_threat_score
from services.alert_service import dispatch_alerts

log = structlog.get_logger()
settings = get_settings()

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


# ── Pydantic schemas ─────────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=10000)
    source: str = Field(default="manual")
    url: Optional[str] = None
    author_id: Optional[str] = None
    author_username: Optional[str] = None
    author_meta: Optional[dict] = {}
    public_metrics: Optional[dict] = {}


class ReportRequest(BaseModel):
    text: str
    url: Optional[str] = None
    source: str = "manual"
    notes: Optional[str] = None


class FeedbackRequest(BaseModel):
    incident_id: str
    is_false_positive: bool
    notes: Optional[str] = None


class AnalyzeResponse(BaseModel):
    content_id: str
    threat_score: int
    severity: str
    categories: List[str]
    language: str
    sentiment: str
    entities: List[str]
    is_coordinated: bool
    bot_probability: float
    recommended_action: str
    score_breakdown: dict


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.redis = await aioredis.from_url(settings.redis_url)
    log.info("API startup complete")
    yield
    await app.state.redis.close()


app = FastAPI(
    title="Anti-India Campaign Detection API",
    version="1.0.0",
    description="AI-powered detection of anti-India disinformation campaigns on digital platforms.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth ──────────────────────────────────────────────────────────────────────
async def verify_api_key(
    api_key: str = Security(API_KEY_HEADER),
    db: AsyncSession = Depends(get_db),
):
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
    )
    key_obj = result.scalar_one_or_none()
    if not key_obj:
        raise HTTPException(status_code=403, detail="Invalid or inactive API key")
    key_obj.last_used_at = datetime.utcnow()
    await db.commit()
    return key_obj


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_content(
    body: AnalyzeRequest,
    request: Request,
    _: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    redis_client: aioredis.Redis = request.app.state.redis
    content_id = f"api:{uuid.uuid4().hex}"

    nlp = analyze_text(body.text)
    bot_prob = estimate_bot_probability(body.author_meta or {})
    coord = await check_coordination(body.text, body.author_id or "", redis_client)
    reach = calculate_reach_score(
        likes=body.public_metrics.get("likes", 0),
        shares=body.public_metrics.get("shares", 0),
        views=body.public_metrics.get("views", 0),
    )
    score_result = compute_threat_score(
        keyword_score=nlp["keyword_score"],
        hate_confidence=nlp["hate_confidence"],
        hate_label=nlp["hate_label"],
        sentiment_score=nlp["sentiment_score"],
        bot_probability=bot_prob,
        coordination_score=coord["coordination_score"],
        reach_score=reach,
    )

    # Optionally save high-severity results
    if score_result["threat_score"] >= 40:
        try:
            source = ContentSource(body.source)
        except ValueError:
            source = ContentSource.manual

        incident = Incident(
            content_id=content_id,
            source=source,
            url=body.url,
            author_id=body.author_id,
            text=body.text[:4000],
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
            reach_score=reach,
            recommended_action=score_result["recommended_action"],
        )
        db.add(incident)
        await db.commit()

        if score_result["threat_score"] >= settings.alert_threshold:
            await dispatch_alerts({**score_result, "source": body.source,
                                   "url": body.url, "text": body.text,
                                   "categories": nlp["categories"],
                                   "language": nlp["language"],
                                   "is_coordinated": coord["is_coordinated"],
                                   "bot_probability": bot_prob})

    return AnalyzeResponse(
        content_id=content_id,
        threat_score=score_result["threat_score"],
        severity=score_result["severity"],
        categories=nlp["categories"],
        language=nlp["language"],
        sentiment=nlp["sentiment"],
        entities=nlp["entities"],
        is_coordinated=coord["is_coordinated"],
        bot_probability=bot_prob,
        recommended_action=score_result["recommended_action"],
        score_breakdown=score_result["score_breakdown"],
    )


@app.get("/api/v1/incidents")
async def list_incidents(
    severity: Optional[str] = None,
    source: Optional[str] = None,
    min_score: int = 0,
    reviewed: Optional[bool] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    _: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    q = select(Incident).order_by(desc(Incident.created_at))
    if severity:
        q = q.where(Incident.severity == severity)
    if source:
        q = q.where(Incident.source == source)
    if min_score:
        q = q.where(Incident.threat_score >= min_score)
    if reviewed is not None:
        q = q.where(Incident.reviewed == reviewed)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    incidents = result.scalars().all()

    count_q = select(func.count(Incident.id))
    total = (await db.execute(count_q)).scalar()
    return {"total": total, "incidents": [i.__dict__ for i in incidents]}


@app.get("/api/v1/incidents/{incident_id}")
async def get_incident(
    incident_id: str,
    _: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident.__dict__


@app.get("/api/v1/stats")
async def get_stats(
    _: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    day_ago = now - timedelta(hours=24)
    hour_ago = now - timedelta(hours=1)

    total = (await db.execute(select(func.count(Incident.id)))).scalar()
    last_24h = (await db.execute(
        select(func.count(Incident.id)).where(Incident.created_at >= day_ago)
    )).scalar()
    last_1h = (await db.execute(
        select(func.count(Incident.id)).where(Incident.created_at >= hour_ago)
    )).scalar()
    critical = (await db.execute(
        select(func.count(Incident.id)).where(Incident.severity == "critical")
    )).scalar()
    avg_score = (await db.execute(select(func.avg(Incident.threat_score)))).scalar() or 0

    return {
        "total_incidents": total,
        "last_24h": last_24h,
        "last_1h": last_1h,
        "critical_count": critical,
        "avg_threat_score": round(avg_score, 1),
    }


@app.get("/api/v1/trends")
async def get_trends(
    hours: int = Query(default=24, le=168),
    _: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(Incident.keywords, Incident.categories, Incident.source)
        .where(Incident.created_at >= since)
        .limit(500)
    )
    rows = result.fetchall()

    keyword_freq: dict[str, int] = {}
    category_freq: dict[str, int] = {}
    source_freq: dict[str, int] = {}

    for keywords, categories, source in rows:
        for kw in (keywords or []):
            keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
        for cat in (categories or []):
            category_freq[cat] = category_freq.get(cat, 0) + 1
        if source:
            source_freq[str(source)] = source_freq.get(str(source), 0) + 1

    top_keywords = sorted(keyword_freq.items(), key=lambda x: -x[1])[:20]
    top_categories = sorted(category_freq.items(), key=lambda x: -x[1])[:10]
    top_sources = sorted(source_freq.items(), key=lambda x: -x[1])

    return {
        "period_hours": hours,
        "top_keywords": [{"keyword": k, "count": c} for k, c in top_keywords],
        "top_categories": [{"category": k, "count": c} for k, c in top_categories],
        "by_source": [{"source": k, "count": c} for k, c in top_sources],
    }


@app.post("/api/v1/report")
async def report_content(
    body: ReportRequest,
    _: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    payload = json.dumps({
        "source": body.source,
        "content_id": f"report:{uuid.uuid4().hex}",
        "text": body.text,
        "url": body.url,
        "notes": body.notes,
        "collected_at": datetime.utcnow().isoformat(),
    })
    # Push directly to analysis queue
    # (In production, import redis and push to stream)
    return {"status": "queued", "message": "Content submitted for analysis"}


@app.post("/api/v1/feedback")
async def submit_feedback(
    body: FeedbackRequest,
    _: ApiKey = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Incident).where(Incident.id == body.incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident.is_false_positive = body.is_false_positive
    incident.reviewed = True
    incident.review_notes = body.notes
    await db.commit()
    return {"status": "updated"}
