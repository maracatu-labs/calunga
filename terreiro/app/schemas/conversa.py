from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.chat import ChatMessage

class ConversaResponse(BaseModel):
    id: UUID
    titulo: str | None = None
    ultima_mensagem: str | None = None
    created_at: datetime
    updated_at: datetime

class ConversaDetail(BaseModel):
    id: UUID
    titulo: str | None = None
    mensagens: list[ChatMessage]
    created_at: datetime
    updated_at: datetime

class ConversaList(BaseModel):
    data: list[ConversaResponse]
