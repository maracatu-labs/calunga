from pydantic import model_validator
from pydantic_settings import BaseSettings

_DEFAULT_JWT_SECRET = "change-me-in-production"
_MIN_JWT_SECRET_LEN = 32

class Settings(BaseSettings):
    model_config = {"env_file": ".env", "extra": "ignore"}

    app_env: str = "development"

    database_url: str = "postgresql://maracatu:changeme@localhost:5432/maracatu"

    redis_url: str = "redis://localhost:6379/0"

    camara_api_url: str = "https://dadosabertos.camara.leg.br/api/v2"
    transparencia_api_token: str = ""

    google_api_key: str = ""
    default_model: str = "gemini-2.5-flash"

    jwt_secret: str = _DEFAULT_JWT_SECRET
    magic_link_ttl_minutes: int = 15
    app_url: str = "http://localhost:3000"

    resend_api_key: str = ""
    email_from: str = "Maracatu <noreply@maracatu.org>"

    magic_link_email_limit_hour: int = 3
    magic_link_ip_limit_hour: int = 10

    token_quota_daily_input: int = 200_000
    token_quota_daily_output: int = 50_000
    max_user_message_chars: int = 8_000
    max_request_chars: int = 60_000

    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    cors_origins: str = "http://localhost:3000,http://localhost:80"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        if self.app_env != "production":
            return self
        if self.jwt_secret == _DEFAULT_JWT_SECRET:
            raise ValueError(
                "JWT_SECRET is still the default value in production. "
                "Generate a strong secret: openssl rand -hex 32"
            )
        if len(self.jwt_secret) < _MIN_JWT_SECRET_LEN:
            raise ValueError(
                f"JWT_SECRET is {len(self.jwt_secret)} chars; minimum is {_MIN_JWT_SECRET_LEN}. "
                "Generate with: openssl rand -hex 32"
            )
        return self

settings = Settings()
