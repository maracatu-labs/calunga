"""Client para API do Portal da Transparência (sanções, CPGF, despesas, contratos, viagens, licitações, emendas)."""

import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"
RATE_LIMIT_DELAY = 0.7

class TransparenciaService:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=30.0,
            headers={
                "chave-api-dados": settings.transparencia_api_token,
                "Accept": "application/json",
            },
        )

    async def _get_paginated(self, endpoint: str, max_pages: int = 100) -> list[dict]:
        """Busca paginada de um endpoint."""
        all_results = []
        page = 1

        while page <= max_pages:
            try:
                resp = await self.client.get(endpoint, params={"pagina": page})
                if resp.status_code == 404 or resp.status_code == 204:
                    break
                resp.raise_for_status()
                data = resp.json()

                if not data:
                    break

                all_results.extend(data)
                logger.info(f"  {endpoint} página {page}: {len(data)} registros")

                if len(data) < 15:
                    break

                page += 1
                await asyncio.sleep(RATE_LIMIT_DELAY)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning("Rate limit atingido, aguardando 60s...")
                    await asyncio.sleep(60)
                    continue
                raise

        return all_results

    async def buscar_ceis(self) -> list[dict]:
        """Busca empresas inidôneas e suspensas (CEIS)."""
        logger.info("Buscando CEIS...")
        return await self._get_paginated("/ceis")

    async def buscar_cnep(self) -> list[dict]:
        """Busca empresas punidas (CNEP)."""
        logger.info("Buscando CNEP...")
        return await self._get_paginated("/cnep")

    async def buscar_cepim(self) -> list[dict]:
        """Busca entidades impedidas (CEPIM)."""
        logger.info("Buscando CEPIM...")
        return await self._get_paginated("/cepim")

    async def buscar_cpgf(self, mes_inicio: str, mes_fim: str, codigo_orgao: str = "") -> list[dict]:
        """Busca gastos do cartão corporativo (CPGF) via endpoint /cartoes.
        mes_inicio/mes_fim no formato MM/YYYY.
        O endpoint /cpgf legado retorna 403; /cartoes e o atual e inclui CPGF,
        CPCC e outros cartoes. Filtramos por tipoCartao.descricao contendo CPGF.
        """
        logger.info(f"Buscando cartões {mes_inicio} a {mes_fim} (órgão: {codigo_orgao or 'todos'})...")
        params = {"mesExtratoInicio": mes_inicio, "mesExtratoFim": mes_fim}
        if codigo_orgao:
            params["codigoOrgao"] = codigo_orgao
        records = await self._get_paginated_with_params("/cartoes", params)

        return [
            r for r in records
            if "CPGF" in ((r.get("tipoCartao") or {}).get("descricao") or "").upper()
        ]

    async def buscar_despesas_orgao(self, ano: int, orgao_superior: str = "") -> list[dict]:
        """Busca execução orçamentária por órgão."""
        logger.info(f"Buscando despesas orçamentárias {ano} (órgão: {orgao_superior or 'todos'})...")
        params = {"ano": ano}
        if orgao_superior:
            params["orgaoSuperior"] = orgao_superior
        return await self._get_paginated_with_params("/despesas/por-orgao", params)

    async def buscar_contratos(self, codigo_orgao: str, data_inicial: str, data_final: str) -> list[dict]:
        """Busca contratos federais. Datas no formato dd/MM/yyyy."""
        logger.info(f"Buscando contratos {codigo_orgao} ({data_inicial} a {data_final})...")
        return await self._get_paginated_with_params("/contratos", {
            "codigoOrgao": codigo_orgao,
            "dataInicial": data_inicial,
            "dataFinal": data_final,
        })

    async def buscar_licitacoes(self, codigo_orgao: str, data_inicial: str, data_final: str) -> list[dict]:
        """Busca licitações federais. Datas no formato dd/MM/yyyy. Max 1 mês."""
        logger.info(f"Buscando licitações {codigo_orgao} ({data_inicial} a {data_final})...")
        return await self._get_paginated_with_params("/licitacoes", {
            "codigoOrgao": codigo_orgao,
            "dataInicial": data_inicial,
            "dataFinal": data_final,
        })

    async def buscar_viagens(self, codigo_orgao: str, data_ida_de: str, data_ida_ate: str) -> list[dict]:
        """Busca viagens a serviço. Datas no formato dd/MM/yyyy."""
        logger.info(f"Buscando viagens {codigo_orgao} ({data_ida_de} a {data_ida_ate})...")
        return await self._get_paginated_with_params("/viagens", {
            "codigoOrgao": codigo_orgao,
            "dataIdaDe": data_ida_de,
            "dataIdaAte": data_ida_ate,
            "dataRetornoDe": data_ida_de,
            "dataRetornoAte": data_ida_ate,
        })

    async def buscar_emendas(self, ano: int) -> list[dict]:
        """Busca emendas parlamentares."""
        logger.info(f"Buscando emendas {ano}...")
        return await self._get_paginated_with_params("/emendas", {"ano": ano})

    async def _get_paginated_with_params(self, endpoint: str, extra_params: dict, max_pages: int = 100) -> list[dict]:
        """Busca paginada com parâmetros extras."""
        all_results = []
        page = 1
        while page <= max_pages:
            try:
                params = {**extra_params, "pagina": page}
                resp = await self.client.get(endpoint, params=params)
                if resp.status_code in (404, 204):
                    break
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    break
                all_results.extend(data)
                logger.info(f"  {endpoint} página {page}: {len(data)} registros")
                if len(data) < 15:
                    break
                page += 1
                await asyncio.sleep(RATE_LIMIT_DELAY)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    logger.warning("Rate limit atingido, aguardando 60s...")
                    await asyncio.sleep(60)
                    continue
                raise
        return all_results

    async def close(self):
        await self.client.aclose()
