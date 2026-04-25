# Anti-India Campaign Detection System

An AI-powered platform to detect, score, and alert on coordinated anti-India disinformation campaigns across digital platforms.

---

## Architecture

```
Data Sources (Twitter, YouTube, Telegram, News RSS)
        ↓  Scrapers / API collectors
Redis Streams (message queue)
        ↓  Worker consumers
AI Pipeline:
  ├── Language Detection  (langdetect / fastText)
  ├── NLP Classifier      (fine-tuned XLM-RoBERTa)
  ├── Sentiment + NER     (spaCy / transformers)
  ├── Network Analysis    (bot + coordination detection)
  ├── Vision AI           (image/video hate scan)
  └── Trend Detection     (hashtag/keyword surge)
        ↓
Threat Scoring Engine     (weighted ensemble 0–100)
        ↓
  ├── Alert System        (email / SMS / webhook)
  ├── PostgreSQL + ES     (incident storage + search)
  └── Analyst Dashboard   (React, live charts)
        ↓
REST API (FastAPI)        → Govt, Platforms, Researchers
```

---

## Quick Start

### Requirements
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Elasticsearch 8+ (optional, for full-text search)

### 1. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in your keys
python -m spacy download en_core_web_sm
alembic upgrade head            # run DB migrations
```

### 2. Start services

```bash
# Terminal 1 — API server
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Content analysis worker
python workers/analysis_worker.py

# Terminal 3 — Data collector (Twitter example)
python workers/collector_worker.py --source twitter
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open **http://localhost:5173**

---

## REST API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/analyze` | Analyze a single piece of content |
| GET  | `/api/v1/incidents` | List detected incidents (paginated) |
| GET  | `/api/v1/incidents/{id}` | Incident detail |
| GET  | `/api/v1/trends` | Trending threats (hashtags, keywords) |
| GET  | `/api/v1/stats` | Dashboard summary statistics |
| POST | `/api/v1/report` | Submit content for manual review |
| POST | `/api/v1/feedback` | Provide label feedback (true/false positive) |
| GET  | `/api/v1/sources` | Active data source status |

### Example: Analyze content

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Sample content to analyze",
    "source": "twitter",
    "url": "https://twitter.com/...",
    "author_id": "12345"
  }'
```

**Response:**
```json
{
  "content_id": "uuid",
  "threat_score": 87,
  "severity": "high",
  "categories": ["hate_speech", "disinformation"],
  "language": "en",
  "sentiment": "negative",
  "entities": ["India", "government"],
  "is_coordinated": true,
  "bot_probability": 0.82,
  "recommended_action": "escalate"
}
```

---

## Threat Scoring

Scores range 0–100:

| Score | Severity | Action |
|-------|----------|--------|
| 0–30  | Low      | Log only |
| 31–60 | Medium   | Flag for review |
| 61–80 | High     | Alert analysts |
| 81–100 | Critical | Escalate immediately |

**Score factors:**
- NLP classification confidence (35%)
- Sentiment intensity (15%)
- Coordination/bot signals (25%)
- Source credibility (10%)
- Reach / viral velocity (15%)

---

## ML Models

| Model | Purpose | Base |
|-------|---------|------|
| `hate_classifier` | Hate speech / propaganda | XLM-RoBERTa |
| `ner_model` | Named entity recognition | spaCy en_core_web_sm |
| `sentiment_model` | Multilingual sentiment | cardiffnlp/twitter-xlm-roberta |
| `bot_detector` | Bot account detection | Random Forest on behavioral features |
| `lang_detector` | Language identification | langdetect |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Uvicorn |
| ML / NLP | Transformers, spaCy, scikit-learn |
| Database | PostgreSQL (incidents), Redis (queue + cache) |
| Search | Elasticsearch |
| Queue | Redis Streams |
| Frontend | React + Vite + Tailwind + Recharts |
| Auth | API key + JWT |
| Alerting | SMTP email, Twilio SMS, webhooks |

---

## Docker

```bash
docker-compose up --build
```

---

## Deploy Frontend on Vercel and Backend on Render

### Render backend

Use the root `render.yaml` blueprint to create:

- `anti-india-api` FastAPI service
- `anti-india-analysis-worker` background worker
- Render PostgreSQL
- Render Redis

Set these Render environment values when prompted:

```bash
BACKEND_CORS_ORIGINS=https://your-vercel-app.vercel.app
BOOTSTRAP_API_KEY=choose-a-long-random-key
```

After Render deploys, copy the API service URL, for example:

```bash
https://anti-india-api.onrender.com
```

### Vercel frontend

Deploy this repository on Vercel. The root `vercel.json` builds the Vite app from `frontend/`.

Set these Vercel environment variables:

```bash
VITE_API_BASE_URL=https://anti-india-api.onrender.com
VITE_API_KEY=the-same-value-as-BOOTSTRAP_API_KEY
```

Then redeploy the Vercel project.
