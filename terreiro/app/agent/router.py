"""Model router: classifica a pergunta do usuario e escolhe o modelo adequado.

- Flash  : queries simples (lista, busca direta, perguntas factuais)
- Pro    : analises complexas (comparacao, anomalias, explicacoes extensas)

Heuristica por regex. A regra de ouro: soh promover para Pro quando o custo
extra faz diferenca qualitativa. Em caso de duvida, fique com Flash — o
fallback automatico em chats.py promove para Pro se o Flash engasgar.
"""

from __future__ import annotations

import re

_COMPLEX_PATTERNS: list[str] = [
    r"compar[ae]\w*",
    r"analis[ae]\w*",
    r"por\s+qu[eê]",
    r"suspeit",
    r"irregular",
    r"anomali",
    r"investig",
    r"evolu[cç][aã]o",
    r"tend[eê]ncia",
    r"padr[aã]o",
    r"cruzar?\s+dados",
    r"correlacion",
    r"detalh\w*\s+(completo|geral|profund)",
]

_COMPLEX_RE = re.compile("|".join(_COMPLEX_PATTERNS), re.IGNORECASE)

_FLASH_MODEL = "gemini-2.5-flash"
_PRO_MODEL = "gemini-2.5-pro"

def route_model(message: str, default_model: str = _FLASH_MODEL) -> str:
    """Retorna o modelo adequado para a pergunta.

    Rankings, listagens e buscas por tipo/nome permanecem no Flash mesmo
    quando envolvem palavras como "ranking", "maiores", "top" — o custo
    comparativo do Pro soh compensa quando a resposta demanda *analise*
    (comparar perfis, investigar padroes, explicar porque algo aconteceu).
    """
    if _COMPLEX_RE.search(message):
        return _PRO_MODEL
    return default_model

def fallback_model(current: str) -> str | None:
    """Retorna o modelo para onde degradar se `current` falhar.

    Pro -> Flash. Flash nao tem fallback (ja e o mais barato); retorna None.
    """
    if current == _PRO_MODEL:
        return _FLASH_MODEL
    return None
