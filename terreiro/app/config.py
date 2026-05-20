from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    model_config = {"env_file": ".env", "extra": "ignore"}

    database_url: str = "postgresql://maracatu:changeme@localhost:5432/maracatu"

    redis_url: str = "redis://localhost:6379/0"

    camara_api_url: str = "https://dadosabertos.camara.leg.br/api/v2"
    transparencia_api_token: str = ""

    google_api_key: str = ""
    default_model: str = "gemini-2.5-flash"

    jwt_secret: str = "change-me-in-production"
    magic_link_ttl_minutes: int = 15
    app_url: str = "http://localhost:3000"

    resend_api_key: str = ""
    email_from: str = "Maracatu <noreply@maracatu.org>"

    cors_origins: str = "http://localhost:3000,http://localhost:80"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

settings = Settings()
