"""Testes dos services (mock HTTP)."""

import pytest
import httpx
from unittest.mock import AsyncMock

from app.services.camara import CamaraService
from app.services.senado import SenadoService, _text, _int_or_none, _float_or_none

class TestCamaraService:
    @pytest.mark.asyncio
    async def test_listar_deputados(self):
        mock_response = httpx.Response(
            200,
            json={"dados": [{"id": 1, "nome": "Teste", "siglaPartido": "PT", "siglaUf": "SP"}]},
            request=httpx.Request("GET", "http://test"),
        )
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=mock_response)

        service = CamaraService(client)
        result = await service.listar_deputados()

        assert len(result) == 1
        assert result[0]["nome"] == "Teste"

    @pytest.mark.asyncio
    async def test_buscar_legislatura_atual(self):
        mock_response = httpx.Response(
            200,
            json={"dados": [{"id": 57}]},
            request=httpx.Request("GET", "http://test"),
        )
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=mock_response)

        service = CamaraService(client)
        result = await service.buscar_legislatura_atual()

        assert result == 57

class TestSenadoHelpers:
    def test_int_or_none_valid(self):
        assert _int_or_none("42") == 42

    def test_int_or_none_empty(self):
        assert _int_or_none("") is None

    def test_int_or_none_none(self):
        assert _int_or_none(None) is None

    def test_float_or_none_comma(self):
        assert _float_or_none("1234,56") == 1234.56

    def test_float_or_none_dot(self):
        assert _float_or_none("1234.56") == 1234.56

    def test_float_or_none_empty(self):
        assert _float_or_none("") is None
