"""
Centralized configuration management using Pydantic Settings.
Loads configuration from environment variables and .env file.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Elasticsearch Configuration
    es_host: str = Field(default="localhost", description="Elasticsearch host")
    es_port: int = Field(default=9200, description="Elasticsearch port")
    es_index: str = Field(default="news_articles", description="Elasticsearch index name")
    es_username: Optional[str] = Field(default=None, description="Elasticsearch username")
    es_password: Optional[str] = Field(default=None, description="Elasticsearch password")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")
    api_title: str = Field(default="News Crawler API", description="API title")
    api_version: str = Field(default="1.0.0", description="API version")

    # Crawler Configuration
    crawler_concurrent_requests: int = Field(default=16, description="Max concurrent requests")
    crawler_concurrent_requests_per_domain: int = Field(default=2, description="Max concurrent requests per domain")
    crawler_download_delay: float = Field(default=0.5, description="Download delay in seconds")
    crawler_user_agent_rotation: bool = Field(default=True, description="Enable user agent rotation")

    # Scheduler Configuration
    scheduler_enabled: bool = Field(default=True, description="Enable scheduled crawling")
    scheduler_interval_minutes: int = Field(default=30, description="Crawling interval in minutes")

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_rotation: str = Field(default="100 MB", description="Log file rotation size")
    log_retention: str = Field(default="30 days", description="Log file retention period")

    # Application Environment
    environment: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=False, description="Debug mode")

    @property
    def es_url(self) -> str:
        """Get full Elasticsearch URL."""
        return f"http://{self.es_host}:{self.es_port}"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"


# Global settings instance
settings = Settings()
