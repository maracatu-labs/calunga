from uuid import UUID

from pydantic import BaseModel

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = True
    model: str | None = None
    conversa_id: UUID | None = None
