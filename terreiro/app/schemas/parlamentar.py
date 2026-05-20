from datetime import datetime

from pydantic import BaseModel

class ParlamentarResponse(BaseModel):
    id: int
    id_externo: str
    tipo: str
    nome: str
    nome_civil: str | None = None
    partido: str | None = None
    uf: str | None = None
    legislatura: int | None = None
    foto_url: str | None = None
    email: str | None = None
    situacao: str | None = None
    created_at: datetime | None = None

class ParlamentarList(BaseModel):
    data: list[ParlamentarResponse]
    total: int
