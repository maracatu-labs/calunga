"""Client para API SICONFI do Tesouro Nacional (dados fiscais de estados e municípios)."""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"

class SiconfiService:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=60.0,
            headers={"Accept": "application/json"},
        )

    async def listar_entes(self) -> list[dict]:
        """Lista todos os entes cadastrados no SICONFI."""
        logger.info("Buscando entes SICONFI...")
        return await self._get("/entes")

    async def buscar_rreo(
        self, id_ente: str, exercicio: int, periodo: int = 6
    ) -> list[dict]:
        """Busca Relatório Resumido de Execução Orçamentária (RREO).
        periodo: 1-6 (bimestral)
        """
        logger.info(f"Buscando RREO {exercicio}/{periodo} ente {id_ente}...")
        params = {
            "an_exercicio": exercicio,
            "nr_periodo": periodo,
            "co_tipo_demonstrativo": "RREO",
            "id_ente": id_ente,
        }
        return await self._get("/rreo", params)

    async def buscar_rgf(
        self, id_ente: str, exercicio: int, periodo: int = 3, esfera: str = "E"
    ) -> list[dict]:
        """Busca Relatório de Gestão Fiscal (RGF).
        periodo: 1-3 (quadrimestral)
        esfera: E=Executivo, L=Legislativo, J=Judiciário, M=Ministério Público
        """
        logger.info(f"Buscando RGF {exercicio}/{periodo} ente {id_ente}...")
        params = {
            "an_exercicio": exercicio,
            "nr_periodo": periodo,
            "co_tipo_demonstrativo": "RGF",
            "co_esfera": esfera,
            "id_ente": id_ente,
        }
        return await self._get("/rgf", params)

    async def buscar_dca(self, id_ente: str, exercicio: int) -> list[dict]:
        """Busca Declaração de Contas Anuais (DCA)."""
        logger.info(f"Buscando DCA {exercicio} ente {id_ente}...")
        params = {
            "an_exercicio": exercicio,
            "id_ente": id_ente,
        }
        return await self._get("/dca", params)

    async def buscar_extratos(self, id_ente: str, exercicio: int) -> list[dict]:
        """Verifica status de entrega dos relatórios de um ente."""
        logger.info(f"Buscando extratos {exercicio} ente {id_ente}...")
        params = {
            "an_referencia": exercicio,
            "id_ente": id_ente,
        }
        return await self._get("/extratos_entregas", params)

    async def _get(self, endpoint: str, params: dict | None = None) -> list[dict]:
        """GET com retry em caso de rate limit."""
        for attempt in range(3):
            try:
                resp = await self.client.get(endpoint, params=params)
                if resp.status_code in (404, 204):
                    return []
                resp.raise_for_status()
                data = resp.json()

                if isinstance(data, dict) and "items" in data:
                    return data["items"]
                if isinstance(data, list):
                    return data
                return []
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait = 30 * (attempt + 1)
                    logger.warning(f"Rate limit SICONFI, aguardando {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                raise
        return []

    async def close(self):
        await self.client.aclose()
