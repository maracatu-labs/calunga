"""Helpers para enriquecer eventos do feed com links auditáveis, severidade
calculada e dados formatados.

Este módulo é a fonte única dos links externos que o usuário usa para
verificar um evento. Todos os publishers devem passar por aqui.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from app.schemas.feed import (
    Acao,
    Ator,
    Contexto,
    DadosFeedRico,
    Evidencia,
    LinkFeed,
    Objeto,
    Severidade,
)


def formatar_brl(valor: float | Decimal | str | None) -> str:
    if valor is None or valor == "":
        return "R$ 0,00"
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "R$ 0,00"
    s = f"R$ {v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_cnpj(cnpj: str | None) -> str | None:
    if not cnpj:
        return None
    digits = "".join(ch for ch in str(cnpj) if ch.isdigit())
    if len(digits) != 14:
        return cnpj
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"

def formatar_cpf(cpf: str | None) -> str | None:
    if not cpf:
        return None
    digits = "".join(ch for ch in str(cpf) if ch.isdigit())
    if len(digits) != 11:
        return cpf
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"

def calcular_severidade(
    *,
    probabilidade: float | None = None,
    valor: float | Decimal | None = None,
    tipo_evento: str | None = None,
) -> Severidade:
    """Combina probabilidade + valor + tipo para decidir severidade visual.

    Regras:
    - tipo empresa_sancionada ou probabilidade >= 0.9 com valor >= 5k vira crítico.
    - probabilidade >= 0.7 ou valor >= 10k vira atenção.
    - resto é informativo.
    """
    prob = float(probabilidade) if probabilidade is not None else 0.0
    val = float(valor) if valor is not None else 0.0

    if tipo_evento in {"empresa_sancionada"} and prob >= 0.7:
        return Severidade.CRITICO
    if prob >= 0.9 and val >= 5_000:
        return Severidade.CRITICO
    if prob >= 0.95:
        return Severidade.CRITICO
    if prob >= 0.7 or val >= 10_000:
        return Severidade.ATENCAO
    return Severidade.INFORMATIVO

def link_camara_deputado(id_externo: str | None) -> LinkFeed | None:
    if not id_externo:
        return None
    return LinkFeed(
        label="Ficha do deputado na Câmara",
        url=f"https://www.camara.leg.br/deputados/{id_externo}",
        tipo="perfil",
    )

def link_senado_senador(id_externo: str | None) -> LinkFeed | None:
    if not id_externo:
        return None

    num = str(id_externo).replace("senado-", "").strip()
    if not num:
        return None
    return LinkFeed(
        label="Ficha do senador no Senado",
        url=f"https://www25.senado.leg.br/web/senadores/senador/-/perfil/{num}",
        tipo="perfil",
    )

def link_recibo(url_documento: str | None) -> LinkFeed | None:
    if not url_documento:
        return None
    return LinkFeed(
        label="Recibo original (PDF)",
        url=url_documento,
        tipo="documento",
    )

def link_busca_cnpj(cnpj: str | None) -> LinkFeed | None:
    """Link para busca do CNPJ no Google. Cobre vários portais (Receita,
    sites de consulta, notícias) de uma só vez, melhor pra auditoria
    do que mandar direto pra Receita (que exige captcha)."""
    if not cnpj:
        return None
    digits = "".join(ch for ch in str(cnpj) if ch.isdigit())
    if len(digits) != 14:
        return None
    formatted = formatar_cnpj(digits) or digits
    from urllib.parse import quote_plus
    return LinkFeed(
        label=f"Buscar {formatted} no Google",
        url=f"https://www.google.com/search?q={quote_plus(formatted)}",
        tipo="consulta",
    )

def link_portal_transparencia_sancao(tipo_sancao: str | None) -> LinkFeed | None:
    if not tipo_sancao:
        return None
    base = "https://portaldatransparencia.gov.br"
    mapa = {
        "CEIS": f"{base}/sancoes/ceis",
        "CNEP": f"{base}/sancoes/cnep",
        "CEPIM": f"{base}/sancoes/cepim",
    }
    url = mapa.get(tipo_sancao.upper())
    if not url:
        return None
    return LinkFeed(
        label=f"Lista {tipo_sancao.upper()} no Portal da Transparência",
        url=url,
        tipo="fonte_oficial",
    )

def link_camara_proposicao(sigla: str | None, numero: int | None, ano: int | None) -> LinkFeed | None:
    if not sigla or not numero or not ano:
        return None
    return LinkFeed(
        label=f"{sigla} {numero}/{ano} no portal da Câmara",
        url=f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=0&tipo={sigla}&numero={numero}&ano={ano}",
        tipo="fonte_oficial",
    )

def link_senado_materia(id_externo: str | None) -> LinkFeed | None:
    if not id_externo:
        return None
    return LinkFeed(
        label="Matéria no portal do Senado",
        url=f"https://www25.senado.leg.br/web/atividade/materias/-/materia/{id_externo}",
        tipo="fonte_oficial",
    )

def link_siop_emendas() -> LinkFeed:
    return LinkFeed(
        label="Emendas no SIOP",
        url="https://www1.siop.planejamento.gov.br/QvAJAXZfc/opendoc.htm?document=IAS%2FExecucao_Orcamentaria.qvw",
        tipo="fonte_oficial",
    )

def construir_dados_ricos(
    *,
    ator: Ator | None = None,
    acao: Acao | None = None,
    objeto: Objeto | None = None,
    evidencia: Evidencia | None = None,
    contexto: Contexto | None = None,
    links: Iterable[LinkFeed | None] = (),
    severidade: Severidade = Severidade.INFORMATIVO,
) -> dict:
    """Monta o payload final pronto para gravar no `feed_eventos.dados`.

    Aceita links None (filtrados) para permitir chamadas diretas com
    builders que devolvem None quando faltam dados.
    """
    dados = DadosFeedRico(
        ator=ator,
        acao=acao,
        objeto=objeto,
        evidencia=evidencia,
        contexto=contexto,
        links=[l for l in links if l is not None],
        severidade=severidade,
    )
    return dados.to_json_dict()
