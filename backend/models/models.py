import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Text, JSON, ForeignKey, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from config.database import Base


class SeverityLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ContentSource(str, enum.Enum):
    twitter = "twitter"
    youtube = "youtube"
    telegram = "telegram"
    news = "news"
    manual = "manual"


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(String(256), unique=True, nullable=False, index=True)
    source = Column(SAEnum(ContentSource), nullable=False)
    url = Column(Text, nullable=True)
    author_id = Column(String(256), nullable=True, index=True)
    author_username = Column(String(256), nullable=True)

    # Raw content
    text = Column(Text, nullable=True)
    media_urls = Column(JSON, default=list)
    language = Column(String(16), default="en")

    # AI analysis results
    threat_score = Column(Integer, default=0)
    severity = Column(SAEnum(SeverityLevel), default=SeverityLevel.low)
    categories = Column(JSON, default=list)       # ["hate_speech", "disinformation", ...]
    sentiment = Column(String(16), nullable=True) # positive / negative / neutral
    sentiment_score = Column(Float, default=0.0)
    entities = Column(JSON, default=list)         # named entities found
    keywords = Column(JSON, default=list)

    # Coordination signals
    is_coordinated = Column(Boolean, default=False)
    bot_probability = Column(Float, default=0.0)
    coordination_cluster = Column(String(256), nullable=True)

    # Reach / virality
    reach_score = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    views = Column(Integer, default=0)

    # Metadata
    recommended_action = Column(String(64), default="log")
    reviewed = Column(Boolean, default=False)
    reviewer_id = Column(String(256), nullable=True)
    review_notes = Column(Text, nullable=True)
    is_false_positive = Column(Boolean, default=False)

    collected_at = Column(DateTime, nullable=True)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    alerts = relationship("Alert", back_populates="incident")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id"))
    channel = Column(String(32))   # email / sms / webhook / slack
    status = Column(String(32), default="sent")
    sent_at = Column(DateTime, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="alerts")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(256), nullable=False)
    key_hash = Column(String(256), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    rate_limit = Column(Integer, default=1000)  # requests per day


class TrendSnapshot(Base):
    __tablename__ = "trend_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_at = Column(DateTime, default=datetime.utcnow, index=True)
    trending_hashtags = Column(JSON, default=list)
    trending_keywords = Column(JSON, default=list)
    incident_count_1h = Column(Integer, default=0)
    incident_count_24h = Column(Integer, default=0)
    avg_threat_score = Column(Float, default=0.0)
    top_sources = Column(JSON, default=list)
