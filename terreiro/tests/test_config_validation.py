"""Tests for the production-mode JWT_SECRET validation."""

import pytest
from pydantic import ValidationError

from app.config import Settings


class TestJwtSecretValidation:
    def test_development_accepts_default_secret(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("JWT_SECRET", "change-me-in-production")
        s = Settings()
        assert s.jwt_secret == "change-me-in-production"

    def test_development_accepts_short_secret(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("JWT_SECRET", "short")
        s = Settings()
        assert s.jwt_secret == "short"

    def test_production_rejects_default_secret(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("JWT_SECRET", "change-me-in-production")
        with pytest.raises(ValidationError) as exc:
            Settings()
        assert "default" in str(exc.value).lower()

    def test_production_rejects_short_secret(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("JWT_SECRET", "x" * 16)
        with pytest.raises(ValidationError) as exc:
            Settings()
        assert "32" in str(exc.value)

    def test_production_accepts_strong_secret(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("JWT_SECRET", "x" * 64)
        s = Settings()
        assert s.app_env == "production"
        assert len(s.jwt_secret) == 64
