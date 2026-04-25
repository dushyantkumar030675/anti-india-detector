from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "changeme"
    api_key_salt: str = "changeme"
    bootstrap_api_key: str = ""

    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/antiindia_db"
    redis_url: str = "redis://localhost:6379/0"
    es_url: str = "http://localhost:9200"
    backend_cors_origins: str = (
        "http://localhost:5173,"
        "http://localhost:3000,"
        "https://dashboard.yourdomain.com,"
        "https://frontend-staging.onrender.com"
    )

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

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if isinstance(value, str):
            if value.startswith("postgres://"):
                return value.replace("postgres://", "postgresql+asyncpg://", 1)
            if value.startswith("postgresql://") and "+asyncpg" not in value:
                return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
