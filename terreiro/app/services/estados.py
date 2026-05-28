"""
Services para portais de transparência estaduais.

Fontes investigadas:
- SP: https://transparencia.tce.sp.gov.br/apis (TCE-SP, XML)
- SP Estado: https://www.transparencia.sp.gov.br/ (dados abertos CSV)
- RJ: https://www.transparencia.rj.gov.br/
- MG: https://www.transparencia.mg.gov.br/

Status: estrutura base criada. APIs estaduais variam muito em formato e disponibilidade.
Implementação detalhada será feita estado por estado conforme prioridade.
"""

import logging

import httpx

logger = logging.getLogger(__name__)

class TransparenciaEstadualSP:
    """Portal de Transparência Municipal do TCE-SP (API XML)."""

    BASE_URL = "https://transparencia.tce.sp.gov.br/api"

    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(timeout=30.0)

    async def buscar_despesas(self, municipio_codigo: str, ano: int) -> list[dict]:
        """Busca despesas de um município de SP."""

        logger.info(f"SP: busca despesas {municipio_codigo}/{ano} (não implementado)")
        return []

    async def close(self):
        await self.client.aclose()

class TransparenciaEstadualRJ:
    """Portal de Transparência do Estado do RJ."""

    BASE_URL = "https://www.transparencia.rj.gov.br"

    async def buscar_despesas(self, ano: int) -> list[dict]:

        logger.info(f"RJ: busca despesas {ano} (não implementado)")
        return []

class TransparenciaEstadualMG:
    """Portal de Transparência do Estado de MG."""

    BASE_URL = "https://www.transparencia.mg.gov.br"

    async def buscar_despesas(self, ano: int) -> list[dict]:

        logger.info(f"MG: busca despesas {ano} (não implementado)")
        return []
