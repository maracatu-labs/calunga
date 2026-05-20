"""Fixtures compartilhadas dos testes.

Decidimos em 2026-04 usar fixtures mockadas (sem container de Postgres)
para manter a suite rapida. A fidelidade e garantida pelo fato das tools
serem thin wrappers sobre queries parametrizadas + formatacao.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

class FakeRecord(dict):
    """Simula asyncpg.Record: acesso por chave, keys(), e iteravel."""

    def keys(self) -> list[str]:  # type: ignore[override]
        return list(super().keys())

@pytest.fixture
def fake_pool():
    """Pool asyncpg mockado. Testes configuram fetch/fetchrow/execute."""
    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=[])
    pool.fetchrow = AsyncMock(return_value=None)
    pool.fetchval = AsyncMock(return_value=None)
    pool.execute = AsyncMock(return_value=None)
    return pool

@pytest.fixture
def install_pool(fake_pool, monkeypatch):
    """Faz get_pool() retornar o fake_pool em qualquer lugar que importar."""
    from app import database
    monkeypatch.setattr(database, "get_pool", lambda: fake_pool)

    from app.agent import tools as tools_module
    monkeypatch.setattr(tools_module, "get_pool", lambda: fake_pool)

    monkeypatch.setattr(tools_module, "_ALIAS_ORGAO_CACHE", None, raising=False)
    return fake_pool

def record(**fields: Any) -> FakeRecord:
    return FakeRecord(**fields)
