"""
Configuration Management for ArXiv Learning Assistant

This module handles all configuration loading from environment variables.
We use python-dotenv to load from .env files and pydantic for validation.

Key Concepts:
- Environment variables keep secrets (API keys) out of code
- Pydantic validates config at startup, failing fast if something is missing
- BaseSettings automatically loads from .env files
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Pydantic's BaseSettings will:
    1. Look for a .env file in the project root
    2. Load environment variables from it
    3. Validate that required fields are present
    4. Provide type conversion (str -> int, etc.)

    If a required field is missing, the app will crash on startup with a clear error.
    This is good! We want to know immediately if configuration is wrong.
    """

    # ============================================================================
    # API Keys - These are REQUIRED for the app to work
    # ============================================================================

    anthropic_api_key: str = Field(
        ...,  # ... means this field is REQUIRED
        alias="ANTHROPIC_API_KEY",
        description="API key for Claude AI from console.anthropic.com",
    )

    # ============================================================================
    # Optional API Keys - These enable additional features
    # ============================================================================

    twitter_bearer_token: str | None = Field(
        default=None,
        alias="TWITTER_BEARER_TOKEN",
        description="Twitter API v2 bearer token (optional, for social signals)",
    )

    semantic_scholar_api_key: str | None = Field(
        default=None,
        alias="SEMANTIC_SCHOLAR_API_KEY",
        description="Semantic Scholar API key (optional, increases rate limits)",
    )

    # ============================================================================
    # Email Settings - For sending daily digests
    # ============================================================================

    smtp_host: str = Field(
        default="smtp.gmail.com", alias="SMTP_HOST", description="SMTP server hostname"
    )

    smtp_port: int = Field(
        default=587,
        alias="SMTP_PORT",
        description="SMTP server port (587 for TLS, 465 for SSL)",
    )

    smtp_username: str | None = Field(
        default=None, alias="SMTP_USERNAME", description="Email address to send from"
    )

    smtp_password: str | None = Field(
        default=None,
        alias="SMTP_PASSWORD",
        description="Email password or app-specific password",
    )

    email_recipient: str | None = Field(
        default=None,
        alias="EMAIL_RECIPIENT",
        description="Email address to send digests to",
    )

    recipient_email: str | None = Field(
        default=None,
        alias="RECIPIENT_EMAIL",
        description="Email address to send digests to (alternative field name)",
    )

    lab_twitter_accounts: str | None = Field(
        default=None,
        alias="LAB_TWITTER_ACCOUNTS",
        description="Comma-separated list of Twitter accounts to track",
    )

    # ============================================================================
    # Research Interests - What topics to track
    # ============================================================================

    research_interests: str = Field(
        default="machine learning,deep learning,natural language processing,computer vision",
        alias="RESEARCH_INTERESTS",
        description="Comma-separated list of research topics",
    )

    arxiv_categories: str = Field(
        default="cs.AI,cs.LG,cs.CL,cs.CV",
        alias="ARXIV_CATEGORIES",
        description="Comma-separated arXiv category codes",
    )

    # ============================================================================
    # Database Settings
    # ============================================================================

    database_url: str = Field(
        default="sqlite:///data/papers.db",
        alias="DATABASE_URL",
        description="SQLAlchemy database URL",
    )

    # ============================================================================
    # Agent Settings - Control behavior and costs
    # ============================================================================

    reader_model: str = Field(
        default="claude-3-5-haiku-20241022",
        alias="READER_MODEL",
        description="Claude model for reading papers (use Haiku for cost efficiency)",
    )

    explainer_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        alias="EXPLAINER_MODEL",
        description="Claude model for explanations (use Sonnet for quality)",
    )

    max_papers_per_digest: int = Field(
        default=5,
        alias="MAX_PAPERS_PER_DIGEST",
        description="How many papers to include in daily email",
    )

    discovery_days_back: int = Field(
        default=1,
        alias="DISCOVERY_DAYS_BACK",
        description="How many days back to search for papers",
    )

    # ============================================================================
    # Research Radar Settings - Background monitoring
    # ============================================================================

    radar_enabled: bool = Field(
        default=False,
        alias="RADAR_ENABLED",
        description="Enable background research radar",
    )

    radar_interval_hours: int = Field(
        default=3,
        alias="RADAR_INTERVAL_HOURS",
        description="How often to run the radar (in hours)",
    )

    radar_start_hour: int = Field(
        default=5,
        alias="RADAR_START_HOUR",
        description="Hour to start radar (24h format, in radar_timezone)",
    )

    radar_end_hour: int = Field(
        default=20,
        alias="RADAR_END_HOUR",
        description="Hour to stop radar (24h format, in radar_timezone)",
    )

    radar_timezone: str = Field(
        default="America/New_York",
        alias="RADAR_TIMEZONE",
        description="Timezone for radar schedule",
    )

    # Notification thresholds (aggressive = lower values)
    notify_breakthrough_threshold: float = Field(
        default=0.6,
        alias="NOTIFY_BREAKTHROUGH_THRESHOLD",
        description="Minimum breakthrough score to trigger notification",
    )

    notify_social_threshold: float = Field(
        default=0.3,
        alias="NOTIFY_SOCIAL_THRESHOLD",
        description="Minimum social score to trigger notification",
    )

    notify_relevance_threshold: float = Field(
        default=0.5,
        alias="NOTIFY_RELEVANCE_THRESHOLD",
        description="Minimum relevance score to trigger notification",
    )

    # ============================================================================
    # Logging
    # ============================================================================

    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    class Config:
        """Pydantic configuration"""

        # Tell pydantic where to find the .env file
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow both uppercase and lowercase env var names
        case_sensitive = False


# ============================================================================
# Global settings instance - Import this in other modules
# ============================================================================

# This will load settings when the module is first imported
# If any required settings are missing, it will raise an error immediately
settings = Settings()


# ============================================================================
# Helper functions
# ============================================================================


def get_research_interests_list() -> list[str]:
    """
    Convert comma-separated research interests string to a list.

    Example:
        "machine learning, NLP, computer vision" -> ["machine learning", "NLP", "computer vision"]
    """
    return [interest.strip() for interest in settings.research_interests.split(",")]


def get_arxiv_categories_list() -> list[str]:
    """
    Convert comma-separated arXiv categories string to a list.

    Example:
        "cs.AI, cs.LG, cs.CL" -> ["cs.AI", "cs.LG", "cs.CL"]
    """
    return [cat.strip() for cat in settings.arxiv_categories.split(",")]


def get_project_root() -> Path:
    """Get the project root directory (where this file lives)."""
    return Path(__file__).parent.parent


def get_data_dir() -> Path:
    """Get the data directory, creating it if it doesn't exist."""
    data_dir = get_project_root() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


def get_logs_dir() -> Path:
    """Get the logs directory, creating it if it doesn't exist."""
    logs_dir = get_project_root() / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir


if __name__ == "__main__":
    # Test that config loads correctly
    print("✅ Configuration loaded successfully!")
    print(f"Research interests: {get_research_interests_list()}")
    print(f"ArXiv categories: {get_arxiv_categories_list()}")
    print(f"Reader model: {settings.reader_model}")
    print(f"Explainer model: {settings.explainer_model}")
