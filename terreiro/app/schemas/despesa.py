from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

class DespesaResponse(BaseModel):
    id: int
    id_externo: str | None = None
    parlamentar_id: int
    parlamentar_nome: str | None = None
    partido: str | None = None
    uf: str | None = None
    ano: int
    mes: int
    data_emissao: date | None = None
    categoria: str
    subcategoria: str | None = None
    fornecedor: str | None = None
    cnpj_cpf: str | None = None
    documento: str | None = None
    valor_documento: Decimal | None = None
    valor_glosa: Decimal | None = None
    valor_liquido: Decimal | None = None
    url_documento: str | None = None
    created_at: datetime | None = None

class DespesaList(BaseModel):
    data: list[DespesaResponse]
    total: int
