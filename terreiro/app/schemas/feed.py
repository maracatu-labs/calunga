"""Contrato padrão dos eventos ricos publicados no feed.

Todos os publishers (asset suspeitas, feed_eventos_dagster, tools do Calunga)
devem montar o campo `dados` seguindo este schema para garantir que o
frontend tenha os mesmos blocos em qualquer tipo de evento.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Severidade(str, Enum):
    CRITICO = "critico"
    ATENCAO = "atencao"
    INFORMATIVO = "informativo"

class LinkFeed(BaseModel):
    """Link externo rastreável que o usuário pode auditar."""

    label: str = Field(description="Texto curto exibido ao usuário")
    url: str
    tipo: Literal[
        "fonte_oficial",
        "documento",
        "consulta",
        "perfil",
        "processo",
    ] = "fonte_oficial"

class Ator(BaseModel):
    """Pessoa ou órgão que praticou a ação."""

    nome: str
    papel: str | None = None
    partido: str | None = None
    uf: str | None = None
    foto_url: str | None = None
    id_externo: str | None = None

class Acao(BaseModel):
    """O que foi feito, quando, com qual valor."""

    verbo: str
    descricao: str
    valor: float | None = None
    valor_formatado: str | None = None
    data: str | None = None
    local: str | None = None

class Objeto(BaseModel):
    """Alvo da ação (fornecedor, proposição, emenda)."""

    tipo: str
    nome: str | None = None
    identificador: str | None = None
    identificador_formatado: str | None = None
    detalhes: dict = Field(default_factory=dict)

class Evidencia(BaseModel):
    """Justificativa da suspeita: classificador, probabilidade, motivo."""

    classificador: str | None = None
    probabilidade: float | None = None
    motivo_humano: str | None = None
    criterios: list[str] = Field(default_factory=list)

class Contexto(BaseModel):
    """Comparações que dão escala ao evento."""

    comparacao_historica: str | None = None
    ranking: str | None = None
    percentual_cota: float | None = None
    alertas: list[str] = Field(default_factory=list)

class DadosFeedRico(BaseModel):
    """Payload padrão serializado no campo `feed_eventos.dados`."""

    ator: Ator | None = None
    acao: Acao | None = None
    objeto: Objeto | None = None
    evidencia: Evidencia | None = None
    contexto: Contexto | None = None
    links: list[LinkFeed] = Field(default_factory=list)
    severidade: Severidade = Severidade.INFORMATIVO
    versao_contrato: int = 1

    def to_json_dict(self) -> dict:
        """Serializa para o formato que vai no JSONB.

        Usa model_dump com mode=json para garantir que enums/decimais virem
        strings/floats compatíveis com asyncpg json.dumps().
        """
        return self.model_dump(mode="json", exclude_none=False)
