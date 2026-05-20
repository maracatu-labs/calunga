import asyncio
import csv
import io
import logging
from xml.etree import ElementTree

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://legis.senado.leg.br/dadosabertos"
CEAP_CSV_URL = "https://www.senado.leg.br/transparencia/LAI/verba/despesa_ceaps_{ano}.csv"
RATE_LIMIT_DELAY = 1.0
MAX_RETRIES = 3
RETRY_DELAY = 5.0

class SenadoService:
    def __init__(self, client: httpx.AsyncClient | None = None):
        self.client = client or httpx.AsyncClient(timeout=30.0)

    async def _get_with_retry(self, url: str, **kwargs) -> httpx.Response:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await self.client.get(url, **kwargs)
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

    async def listar_senadores(self) -> list[dict]:
        """Busca senadores em exercício via API XML do Senado."""
        resp = await self._get_with_retry(
            f"{BASE_URL}/senador/lista/atual",
            headers={"Accept": "application/xml"},
        )

        root = ElementTree.fromstring(resp.text)
        senadores = []

        for parlamentar in root.iter("Parlamentar"):
            dados = parlamentar.find("IdentificacaoParlamentar")
            if dados is None:
                continue

            senadores.append({
                "codigo": _text(dados, "CodigoParlamentar"),
                "nome": _text(dados, "NomeParlamentar"),
                "nome_completo": _text(dados, "NomeCompletoParlamentar"),
                "partido": _text(dados, "SiglaPartidoParlamentar"),
                "uf": _text(dados, "UfParlamentar"),
                "foto_url": _text(dados, "UrlFotoParlamentar"),
                "email": _text(dados, "EmailParlamentar"),
            })

        return senadores

    async def buscar_despesas_csv(self, ano: int) -> list[dict]:
        """Download e parse do CSV de despesas CEAP do Senado."""
        url = CEAP_CSV_URL.format(ano=ano)
        logger.info(f"Baixando CSV do Senado: {url}")

        resp = await self._get_with_retry(url)

        try:
            text = resp.content.decode("utf-8")
        except UnicodeDecodeError:
            text = resp.content.decode("latin-1")

        lines = text.strip().split("\n")

        header_idx = 0
        for i, line in enumerate(lines):
            if '"ANO"' in line or "ANO" in line.split(";")[0]:
                header_idx = i
                break
        csv_text = "\n".join(lines[header_idx:])

        reader = csv.DictReader(io.StringIO(csv_text), delimiter=";", quotechar='"')
        despesas = []
        for row in reader:
            despesas.append({
                "ano": _int_or_none(row.get("ANO")),
                "mes": _int_or_none(row.get("MES")),
                "senador": row.get("SENADOR", "").strip(),
                "tipo_despesa": row.get("TIPO_DESPESA", "").strip(),
                "cnpj_cpf": row.get("CNPJ_CPF", "").strip(),
                "fornecedor": row.get("FORNECEDOR", "").strip(),
                "documento": row.get("DOCUMENTO", "").strip(),
                "data": row.get("DATA", "").strip(),
                "valor_reembolsado": _float_or_none(row.get("VALOR_REEMBOLSADO")),
            })

        logger.info(f"Senado {ano}: {len(despesas)} despesas no CSV")
        return despesas

    async def listar_votacoes(self, page_size: int = 20, ano: int | None = None) -> list[dict]:
        """Busca votações do Senado via nova API (retorna votos inline)."""
        logger.info(f"Buscando votações do Senado{f' ({ano})' if ano else ''}...")
        params: dict = {"pageSize": page_size}
        if ano:
            params["ano"] = ano
        resp = await self._get_with_retry(
            "https://legis.senado.leg.br/dadosabertos/votacao",
            params=params,
            headers={"Accept": "application/json"},
        )
        data = resp.json()
        return data if isinstance(data, list) else []

    async def close(self):
        await self.client.aclose()

def _text(element, tag: str) -> str | None:
    child = element.find(tag)
    return child.text.strip() if child is not None and child.text else None

def _int_or_none(val) -> int | None:
    if not val:
        return None
    try:
        return int(val.strip())
    except (ValueError, AttributeError):
        return None

def _float_or_none(val) -> float | None:
    if not val:
        return None
    try:
        return float(val.strip().replace(",", "."))
    except (ValueError, AttributeError):
        return None
