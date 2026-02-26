# =============================================================================
# Environment configuration using Pydantic Settings
# =============================================================================
#
# Loads configuration from environment variables or .env file.
# All sensitive values come from .env (gitignored).
#
# WordPress API namespaces (journey-os):
#   RTR Reading Room: /wp-json/directreach/v1/reading-room/
#   Campaign Builder:  /wp-json/directreach/v2/
# =============================================================================

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application settings loaded from environment

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # WordPress Integration
    wordpress_base_url: str = "https://example.com"
    wordpress_api_key: str = ""

    # WordPress Application Passwords (Phase 1+)
    # Used for Basic Auth to satisfy current_user_can() on REST endpoints
    # Create at: WordPress Admin > Users > Your Profile > Application Passwords
    wordpress_app_user: str = ""
    wordpress_app_password: str = ""

    # LLM API Keys
    anthropic_api_key: str = ""
    gemini_api_key: str = ""

    # Timeouts
    api_timeout_seconds: int = 30

    # LLM Settings (Phase 3+)
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 1024

    # Gemini Settings (Phase 5)
    gemini_model: str = "gemini-2.0-flash"
    gemini_max_tokens: int = 2048

    @property
    def has_wordpress_auth(self) -> bool:
        # Check if WordPress Application Password credentials are configured
        return bool(self.wordpress_app_user and self.wordpress_app_password)

    @property
    def has_anthropic_key(self) -> bool:
        # Check if Anthropic API key is configured
        return bool(self.anthropic_api_key)

    @property
    def has_gemini_key(self) -> bool:
        # Check if Gemini API key is configured
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    # Get cached settings instance
    return Settings()


# Convenience instance
settings = get_settings()
