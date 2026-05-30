from typing import Literal

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    tipo: Literal["like", "dislike"]
    categoria: str | None = Field(default=None, max_length=40)
    comentario: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    ok: bool
    tipo: str
