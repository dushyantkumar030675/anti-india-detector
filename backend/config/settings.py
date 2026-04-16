from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "changeme"
    api_key_salt: str = "changeme"

    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/antiindia_db"
    redis_url: str = "redis://localhost:6379/0"
    es_url: str = "http://localhost:9200"

    twitter_bearer_token: str = ""
    youtube_api_key: str = ""
    openai_api_key: str = ""

    sendgrid_api_key: str = ""
    alert_email_from: str = ""
    alert_email_to: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    alert_sms_to: str = ""

    alert_webhook_url: str = ""

    hate_model_path: str = "cardiffnlp/twitter-roberta-base-hate"
    sentiment_model_path: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment"

    # Scoring weights (must sum to 1.0)
    weight_classification: float = 0.35
    weight_sentiment: float = 0.15
    weight_coordination: float = 0.25
    weight_source: float = 0.10
    weight_reach: float = 0.15

    # Thresholds
    alert_threshold: int = 61
    critical_threshold: int = 81

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
