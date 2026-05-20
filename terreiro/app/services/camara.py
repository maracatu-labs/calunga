import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = settings.camara_api_url
RATE_LIMIT_DELAY = 1.0
MAX_RETRIES = 3
RETRY_DELAY = 5.0

class CamaraService:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=30.0,
            headers={"Accept": "application/json"},
        )

    async def _get_with_retry(self, url: str, params: dict | None = None) -> httpx.Response:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await self.client.get(url, params=params)
                if resp.status_code in (502, 503, 504, 429):
                    logger.warning(f"HTTP {resp.status_code} em {url} (tentativa {attempt}/{MAX_RETRIES})")
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_DELAY * attempt)
                        continue
                resp.raise_for_status()
                return resp
            except httpx.ConnectError as e:
                logger.warning(f"Erro de conexão em {url} (tentativa {attempt}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * attempt)
                else:
                    raise
        raise httpx.HTTPStatusError("Max retries exceeded", request=None, response=resp)

    async def listar_deputados(
        self,
        *,
        legislatura: int | None = None,
        uf: str | None = None,
        partido: str | None = None,
        pagina: int = 1,
        itens: int = 100,
    ) -> list[dict]:
        params: dict = {"pagina": pagina, "itens": itens, "ordem": "ASC", "ordenarPor": "nome"}
        if legislatura:
            params["idLegislatura"] = legislatura
        if uf:
            params["siglaUf"] = uf
        if partido:
            params["siglaPartido"] = partido

        resp = await self._get_with_retry("/deputados", params=params)
        return resp.json()["dados"]

    async def listar_todos_deputados(self, legislatura: int | None = None) -> list[dict]:
        todos = []
        pagina = 1
        while True:
            lote = await self.listar_deputados(legislatura=legislatura, pagina=pagina, itens=100)
            if not lote:
                break
            todos.extend(lote)
            pagina += 1
            await asyncio.sleep(RATE_LIMIT_DELAY)
        return todos

    async def buscar_deputado(self, deputado_id: int) -> dict:
        resp = await self._get_with_retry(f"/deputados/{deputado_id}")
        return resp.json()["dados"]

    async def buscar_despesas(
        self,
        deputado_id: int,
        *,
        ano: int | None = None,
        mes: int | None = None,
        pagina: int = 1,
        itens: int = 100,
    ) -> list[dict]:
        params: dict = {"pagina": pagina, "itens": itens, "ordem": "DESC", "ordenarPor": "ano"}
        if ano:
            params["ano"] = ano
        if mes:
            params["mes"] = mes

        resp = await self._get_with_retry(f"/deputados/{deputado_id}/despesas", params=params)
        return resp.json()["dados"]

    async def buscar_todas_despesas(
        self,
        deputado_id: int,
        *,
        ano: int | None = None,
    ) -> list[dict]:
        todas = []
        pagina = 1
        while True:
            lote = await self.buscar_despesas(deputado_id, ano=ano, pagina=pagina, itens=100)
            if not lote:
                break
            todas.extend(lote)
            pagina += 1
            await asyncio.sleep(RATE_LIMIT_DELAY)
        return todas

    async def buscar_legislatura_atual(self) -> int:
        resp = await self._get_with_retry("/legislaturas", params={"ordem": "DESC", "ordenarPor": "id", "itens": 1})
        dados = resp.json()["dados"]
        return dados[0]["id"] if dados else 57

    async def listar_votacoes(
        self, data_inicio: str, data_fim: str, pagina: int = 1, itens: int = 100
    ) -> list[dict]:
        """Lista votações em plenário. Datas no formato YYYY-MM-DD."""
        params = {
            "dataInicio": data_inicio,
            "dataFim": data_fim,
            "ordem": "DESC",
            "ordenarPor": "dataHoraRegistro",
            "pagina": pagina,
            "itens": itens,
        }
        resp = await self._get_with_retry("/votacoes", params=params)
        return resp.json().get("dados", [])

    async def listar_todas_votacoes(self, data_inicio: str, data_fim: str) -> list[dict]:
        todas = []
        pagina = 1
        while True:
            lote = await self.listar_votacoes(data_inicio, data_fim, pagina=pagina)
            if not lote:
                break
            todas.extend(lote)
            pagina += 1
            await asyncio.sleep(RATE_LIMIT_DELAY)
        return todas

    async def buscar_votacao(self, votacao_id: str) -> dict:
        resp = await self._get_with_retry(f"/votacoes/{votacao_id}")
        return resp.json().get("dados", {})

    async def buscar_votos(self, votacao_id: str) -> list[dict]:
        resp = await self._get_with_retry(f"/votacoes/{votacao_id}/votos")
        return resp.json().get("dados", [])

    async def buscar_orientacoes(self, votacao_id: str) -> list[dict]:
        resp = await self._get_with_retry(f"/votacoes/{votacao_id}/orientacoes")
        return resp.json().get("dados", [])

    async def close(self):
        await self.client.aclose()
