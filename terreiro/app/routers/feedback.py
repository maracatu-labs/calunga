import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.database import get_pool
from app.queries import feedback as feedback_q
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/v1", tags=["feedback"])


@router.post("/mensagens/{mensagem_id}/feedback", response_model=FeedbackResponse)
async def registrar_feedback(
    mensagem_id: int,
    body: FeedbackCreate,
    current_user: dict = Depends(get_current_user),
):
    pool = get_pool()
    user_id = uuid.UUID(current_user["id"])
    inserted = await feedback_q.registrar_feedback(
        pool, mensagem_id, user_id, body.tipo, body.categoria, body.comentario,
    )
    if not inserted:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada")
    return FeedbackResponse(ok=True, tipo=body.tipo)
