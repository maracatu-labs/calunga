from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ConversaResponse(BaseModel):
    id: UUID
    titulo: str | None = None
    ultima_mensagem: str | None = None
    created_at: datetime
    updated_at: datetime

class ConversaMessage(BaseModel):
    """A persisted message in a conversation detail response.

    Carries the database id (needed by the client to submit feedback), the
    persisted tool activity (tool_start/tool_end events captured during the
    stream) and the caller's latest feedback vote, when authenticated.
    """

    id: int
    role: str
    content: str
    tool_calls: list[Any] | None = None
    feedback: str | None = None

class ConversaDetail(BaseModel):
    id: UUID
    titulo: str | None = None
    mensagens: list[ConversaMessage]
    created_at: datetime
    updated_at: datetime

class ConversaList(BaseModel):
    data: list[ConversaResponse]
