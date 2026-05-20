"""Client para consulta de CNPJ via BrasilAPI (fallback on-demand)."""

import logging

import asyncpg
import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://brasilapi.com.br/api/cnpj/v1"

async def consultar_cnpj(cnpj: str, pool: asyncpg.Pool | None = None) -> dict | None:
    """Consulta CNPJ na BrasilAPI e opcionalmente cacheia no banco."""
    digits = cnpj.replace(".", "").replace("/", "").replace("-", "").strip()
    if len(digits) != 14:
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{BASE_URL}/{digits}")
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning(f"BrasilAPI erro para {digits}: {e}")
        return None

    result = {
        "cnpj": digits,
        "razao_social": data.get("razao_social"),
        "nome_fantasia": data.get("nome_fantasia"),
        "situacao_cadastral": _map_situacao(data.get("descricao_situacao_cadastral")),
        "data_situacao": data.get("data_situacao_cadastral"),
        "natureza_juridica": data.get("natureza_juridica"),
        "atividade_principal_codigo": (data.get("cnae_fiscal") or ""),
        "atividade_principal_descricao": data.get("cnae_fiscal_descricao"),
        "logradouro": data.get("logradouro"),
        "municipio": data.get("municipio"),
        "uf": data.get("uf"),
        "cep": (data.get("cep") or "").replace("-", ""),
        "capital_social": data.get("capital_social"),
        "data_abertura": data.get("data_inicio_atividade"),
        "porte": _map_porte(data.get("porte")),
    }

    if pool:
        try:
            await pool.execute(
                """
                INSERT INTO empresas (cnpj, razao_social, nome_fantasia, situacao_cadastral,
                                      data_situacao, natureza_juridica, atividade_principal_codigo,
                                      atividade_principal_descricao, logradouro, municipio, uf,
                                      cep, capital_social, data_abertura, porte, fonte)
                VALUES ($1,$2,$3,$4,$5::date,$6,$7,$8,$9,$10,$11,$12,$13,$14::date,$15,'api')
                ON CONFLICT (cnpj) DO UPDATE SET
                    razao_social = EXCLUDED.razao_social,
                    situacao_cadastral = EXCLUDED.situacao_cadastral,
                    data_situacao = EXCLUDED.data_situacao,
                    updated_at = NOW()
                """,
                digits,
                result["razao_social"],
                result["nome_fantasia"],
                result["situacao_cadastral"],
                result["data_situacao"],
                result["natureza_juridica"],
                str(result["atividade_principal_codigo"]),
                result["atividade_principal_descricao"],
                result["logradouro"],
                result["municipio"],
                result["uf"],
                result["cep"],
                result["capital_social"],
                result["data_abertura"],
                result["porte"],
            )
        except Exception as e:
            logger.warning(f"Erro cacheando CNPJ {digits}: {e}")

    return result

def _map_situacao(desc: str | None) -> str:
    if not desc:
        return "DESCONHECIDA"
    return desc.upper()

def _map_porte(val) -> str | None:
    if not val:
        return None
    mapping = {
        "01": "MICRO EMPRESA",
        "03": "EMPRESA DE PEQUENO PORTE",
        "05": "DEMAIS",
    }
    return mapping.get(str(val), str(val))
