"""Testes do cache de respostas (chaveamento por conversa)."""

from unittest.mock import AsyncMock

import pytest

from app import cache as cache_module


class TestCacheKey:
    def test_mesma_pergunta_em_conversas_diferentes_tem_keys_distintas(self):
        k1 = cache_module._cache_key("Quem e ele?", "flash", "conv-a")
        k2 = cache_module._cache_key("Quem e ele?", "flash", "conv-b")
        assert k1 != k2

    def test_mesma_pergunta_mesma_conversa_e_deterministica(self):
        k1 = cache_module._cache_key("Quem e ele?", "flash", "conv-a")
        k2 = cache_module._cache_key("Quem e ele?", "flash", "conv-a")
        assert k1 == k2

    def test_normaliza_case_e_espacos(self):
        k1 = cache_module._cache_key("Pergunta", "flash", "c")
        k2 = cache_module._cache_key("  pergunta ", "flash", "c")
        assert k1 == k2

    def test_modelo_diferente_key_diferente(self):
        k1 = cache_module._cache_key("x", "flash", "c")
        k2 = cache_module._cache_key("x", "pro", "c")
        assert k1 != k2

    def test_sem_conversa_id_usa_bucket_global(self):
        k1 = cache_module._cache_key("x", "flash", None)
        k2 = cache_module._cache_key("x", "flash", "")
        assert k1 == k2

    def test_semantic_key_segue_bucket(self):
        assert cache_module._semantic_key("abc") == "semcache:abc"
        assert cache_module._semantic_key(None) == "semcache:global"

class TestCosineSimilarity:
    def test_vetores_iguais_dao_um(self):
        a = [1.0, 2.0, 3.0]
        assert abs(cache_module._cosine_similarity(a, a) - 1.0) < 1e-9

    def test_vetores_ortogonais_dao_zero(self):
        assert cache_module._cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0

    def test_tamanhos_diferentes_retorna_zero(self):
        assert cache_module._cosine_similarity([1.0, 2.0], [1.0]) == 0.0

    def test_vetor_zero_retorna_zero(self):
        assert cache_module._cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

class TestCacheOperations:
    @pytest.mark.asyncio
    async def test_get_cache_hit(self, monkeypatch):
        fake_redis = AsyncMock()
        fake_redis.get = AsyncMock(return_value="resposta cacheada")
        monkeypatch.setattr(cache_module, "get_redis", AsyncMock(return_value=fake_redis))

        result = await cache_module.get_cached_response("pergunta", "flash", conversa_id="c1")
        assert result == "resposta cacheada"
        fake_redis.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_cache_aplica_ttl(self, monkeypatch):
        fake_redis = AsyncMock()
        fake_redis.set = AsyncMock()
        monkeypatch.setattr(cache_module, "get_redis", AsyncMock(return_value=fake_redis))

        await cache_module.set_cached_response("pergunta", "flash", "resposta", conversa_id="c1")
        _, kwargs = fake_redis.set.call_args
        assert kwargs.get("ex") == cache_module.CACHE_TTL

    @pytest.mark.asyncio
    async def test_get_cache_miss_retorna_none(self, monkeypatch):
        fake_redis = AsyncMock()
        fake_redis.get = AsyncMock(return_value=None)
        monkeypatch.setattr(cache_module, "get_redis", AsyncMock(return_value=fake_redis))

        result = await cache_module.get_cached_response("x", "flash", conversa_id="c1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cache_degrada_sem_redis(self, monkeypatch):
        async def broken():
            raise RuntimeError("redis down")
        monkeypatch.setattr(cache_module, "get_redis", broken)

        result = await cache_module.get_cached_response("x", "flash", conversa_id="c1")
        assert result is None
