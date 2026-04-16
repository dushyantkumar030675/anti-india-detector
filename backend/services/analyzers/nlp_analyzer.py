"""
NLP Analysis Service
Runs hate/propaganda classification, sentiment analysis, and NER.
Models load once at startup and are reused.
"""
from __future__ import annotations
import re
import structlog
from langdetect import detect, LangDetectException
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import spacy
from config.settings import get_settings

log = structlog.get_logger()
settings = get_settings()

# ── Keyword lists ────────────────────────────────────────────────────────────
ANTI_INDIA_KEYWORDS = [
    "india terrorist", "india genocide", "modi fascist", "hindu extremist",
    "india occupier", "down with india", "india colonizer", "kashmiri genocide",
    "india oppressor", "boycott india", "india war criminal", "bharat murdabad",
    "india is evil", "indian army atrocities", "hindu nationalism danger",
    "india is a threat", "india state terrorism",
]

PROPAGANDA_PATTERNS = [
    r"\b(fake|fabricated|staged)\s+(attack|incident|news)\b",
    r"\b(india|modi|bjp)\s+(is|are)\s+(terrorist|fascist|nazi)\b",
    r"\bkill\s+(hindus|indians|modi)\b",
    r"\b(destroy|burn|destroy)\s+india\b",
]

# ── Model singletons ─────────────────────────────────────────────────────────
_hate_classifier = None
_sentiment_pipeline = None
_nlp = None  # spaCy


def _load_models():
    global _hate_classifier, _sentiment_pipeline, _nlp
    if _hate_classifier is None:
        log.info("Loading hate classifier model...")
        try:
            _hate_classifier = pipeline(
                "text-classification",
                model=settings.hate_model_path,
                truncation=True,
                max_length=512,
            )
        except Exception as e:
            log.warning("Could not load hate model, using keyword fallback", error=str(e))

    if _sentiment_pipeline is None:
        log.info("Loading sentiment model...")
        try:
            _sentiment_pipeline = pipeline(
                "text-classification",
                model=settings.sentiment_model_path,
                truncation=True,
                max_length=512,
            )
        except Exception as e:
            log.warning("Could not load sentiment model", error=str(e))

    if _nlp is None:
        log.info("Loading spaCy model...")
        try:
            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            log.warning("spaCy model not found", error=str(e))


# ── Language detection ───────────────────────────────────────────────────────
def detect_language(text: str) -> str:
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


# ── Keyword + regex scan ─────────────────────────────────────────────────────
def keyword_scan(text: str) -> dict:
    text_lower = text.lower()
    matched_keywords = [kw for kw in ANTI_INDIA_KEYWORDS if kw in text_lower]
    matched_patterns = []
    for pattern in PROPAGANDA_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            matched_patterns.append(pattern)
    return {
        "keywords": matched_keywords,
        "patterns": matched_patterns,
        "keyword_score": min(len(matched_keywords) * 15 + len(matched_patterns) * 20, 100),
    }


# ── Hate speech classification ───────────────────────────────────────────────
def classify_hate(text: str) -> dict:
    _load_models()
    result = {"label": "not_hate", "confidence": 0.0, "categories": []}

    if _hate_classifier:
        try:
            out = _hate_classifier(text[:512])[0]
            label = out["label"].lower()
            score = out["score"]
            result["label"] = label
            result["confidence"] = score
            if "hate" in label or score > 0.7:
                result["categories"].append("hate_speech")
        except Exception as e:
            log.warning("Hate classifier error", error=str(e))

    # Supplement with keyword scan
    kw = keyword_scan(text)
    if kw["keywords"] or kw["patterns"]:
        if "disinformation" not in result["categories"]:
            result["categories"].append("propaganda")
    result["keyword_matches"] = kw["keywords"]

    return result


# ── Sentiment analysis ───────────────────────────────────────────────────────
def analyze_sentiment(text: str) -> dict:
    _load_models()
    result = {"label": "neutral", "score": 0.0}
    if _sentiment_pipeline:
        try:
            out = _sentiment_pipeline(text[:512])[0]
            label = out["label"].lower()
            score = out["score"]
            if "neg" in label:
                result = {"label": "negative", "score": -score}
            elif "pos" in label:
                result = {"label": "positive", "score": score}
            else:
                result = {"label": "neutral", "score": 0.0}
        except Exception as e:
            log.warning("Sentiment error", error=str(e))
    return result


# ── Named entity recognition ─────────────────────────────────────────────────
def extract_entities(text: str) -> list[str]:
    _load_models()
    if not _nlp:
        return []
    try:
        doc = _nlp(text[:1000])
        return list({ent.text for ent in doc.ents if ent.label_ in {
            "GPE", "ORG", "PERSON", "NORP", "LOC", "FAC", "EVENT"
        }})
    except Exception as e:
        log.warning("NER error", error=str(e))
        return []


# ── Full analysis pipeline ───────────────────────────────────────────────────
def analyze_text(text: str) -> dict:
    lang = detect_language(text)
    hate = classify_hate(text)
    sentiment = analyze_sentiment(text)
    entities = extract_entities(text)
    kw = keyword_scan(text)

    categories = list(set(hate.get("categories", [])))

    return {
        "language": lang,
        "hate_label": hate["label"],
        "hate_confidence": hate["confidence"],
        "categories": categories,
        "sentiment": sentiment["label"],
        "sentiment_score": sentiment["score"],
        "entities": entities,
        "keywords": kw["keywords"],
        "keyword_score": kw["keyword_score"],
    }
