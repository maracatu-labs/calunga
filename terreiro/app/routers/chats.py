import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from app.agent.graph import create_agent, get_agent_config
from app.agent.router import fallback_model, route_model
from app.agent.stream import stream_agent_response
from app.auth import get_current_user
from app.cache import get_cached_response, set_cached_response
from app.config import settings
from app.database import get_pool
from app.metrics import incr, incr_by_dim, time_ms
from app.queries import conversas as conversas_q
from app.schemas.chat import ChatRequest
from app.schemas.conversa import ConversaDetail, ConversaList, ConversaResponse
from app.services import token_quota

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chats"])

async def _ainvoke_with_fallback(model: str, messages: list, config: dict | None):
    """Invoca o agente com fallback Pro->Flash em caso de erro.

    Se o Pro falhar (rate limit, timeout, quota), recria o agente com Flash
    e tenta de novo. Flash nao tem fallback; se ele falhar, o erro sobe.
    Retorna (resultado_do_agente, modelo_que_respondeu).
    """
    agent = create_agent(model=model)
    try:
        async with time_ms(f"chat.ainvoke.{model}"):
            result = await agent.ainvoke({"messages": messages}, config=config)
        await incr_by_dim("model.used", model)
        return result, model
    except Exception as primary_err:
        fb = fallback_model(model)
        if not fb:
            await incr("chat.error")
            raise
        logger.warning(
            "Agent primary model %s falhou (%s); tentando fallback %s",
            model, primary_err, fb,
        )
        await incr_by_dim("model.fallback", f"{model}->{fb}")
        agent = create_agent(model=fb)
        async with time_ms(f"chat.ainvoke.{fb}"):
            result = await agent.ainvoke({"messages": messages}, config=config)
        await incr_by_dim("model.used", fb)
        return result, fb

@router.post("/chats")
async def create_chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    last_user = next((m for m in reversed(request.messages) if m.role == "user"), None)
    if last_user and len(last_user.content) > settings.max_user_message_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Mensagem muito longa. Limite: {settings.max_user_message_chars} caracteres.",
        )
    total_chars = sum(len(m.content) for m in request.messages)
    if total_chars > settings.max_request_chars:
        raise HTTPException(
            status_code=413,
            detail="Conversa muito longa para enviar. Inicie uma nova consulta.",
        )

    await token_quota.check_quota(current_user["id"])

    pool = get_pool()
    last_user_msg = last_user.content if last_user else ""
    model = request.model or route_model(last_user_msg, settings.default_model)

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    conversa_id = request.conversa_id
    if not conversa_id:

        first_user_msg = next((m.content for m in request.messages if m.role == "user"), "")
        titulo = first_user_msg[:80].strip() or "Nova consulta"
        user_id = uuid.UUID(current_user["id"])
        conversa_id = await conversas_q.criar_conversa(pool, titulo, user_id=user_id)

    if last_user:
        await conversas_q.adicionar_mensagem(pool, conversa_id, "user", last_user.content)

    agent_config = get_agent_config()

    if request.stream:
        agent = create_agent(model=model)
        return EventSourceResponse(
            _stream_and_persist(
                agent, messages, pool, conversa_id, agent_config,
                user_id=current_user["id"], input_chars=total_chars,
            ),
            media_type="text/event-stream",
            headers={"X-Conversa-Id": str(conversa_id)},
        )

    last_user_content = last_user.content if last_user else ""
    cached = await get_cached_response(last_user_content, model, conversa_id=str(conversa_id))
    if cached:
        await incr("cache.hit")
        logger.info("chat cache_hit conversa=%s model=%s", conversa_id, model)
        await conversas_q.adicionar_mensagem(pool, conversa_id, "assistant", cached)
        return {"role": "assistant", "content": cached, "conversa_id": str(conversa_id)}

    await incr("cache.miss")

    result, model_used = await _ainvoke_with_fallback(model, messages, agent_config)
    last_message = result["messages"][-1]
    content = _extract_text(last_message.content)
    await conversas_q.adicionar_mensagem(pool, conversa_id, "assistant", content)
    await set_cached_response(last_user_content, model_used, content, conversa_id=str(conversa_id))
    await token_quota.record_usage(current_user["id"], total_chars, len(content))
    return {
        "role": "assistant",
        "content": content,
        "conversa_id": str(conversa_id),
        "model": model_used,
    }

def _extract_text(content) -> str:
    """Extract text from LangChain message content (can be str or list of blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
        return "".join(parts)
    return str(content)

async def _stream_and_persist(
    agent, messages, pool, conversa_id, config=None,
    user_id: str | None = None, input_chars: int = 0,
):
    """Stream agent response and persist the full assistant message at the end.

    Besides the final text, this collects the tool_start/tool_end events so the
    activity timeline can be rebuilt on reload, and emits a final `message` event
    carrying the persisted message id (the client needs it to submit feedback).
    The inner [DONE] is swallowed so we can persist first and emit our own.
    """
    import json

    full_response: list[str] = []
    tool_events: list[dict] = []

    async for event in stream_agent_response(agent, messages, config=config):
        if isinstance(event, dict) and event.get("data") == "[DONE]":
            # Persist before signalling completion; we emit [DONE] ourselves below.
            continue

        yield event

        if isinstance(event, dict) and "data" in event:
            try:
                data = json.loads(event["data"])
            except (json.JSONDecodeError, TypeError):
                continue
            kind = data.get("type")
            if kind == "text" and data.get("content"):
                full_response.append(data["content"])
            elif kind == "tool_start":
                tool_events.append({
                    "type": "tool_start",
                    "tool": data.get("tool"),
                    "args": data.get("args") or {},
                })
            elif kind == "tool_end":
                event_payload = {"type": "tool_end", "tool": data.get("tool"), "status": data.get("status")}
                if data.get("error"):
                    event_payload["error"] = data["error"]
                tool_events.append(event_payload)

    message_id: int | None = None
    if full_response:
        content = "".join(full_response)
        row = await conversas_q.adicionar_mensagem(
            pool, conversa_id, "assistant", content, tool_calls=tool_events or None,
        )
        message_id = row["id"]
        if user_id:
            await token_quota.record_usage(user_id, input_chars, len(content))

    if message_id is not None:
        yield {"data": json.dumps({"type": "message", "id": message_id})}
    yield {"data": "[DONE]"}

@router.get("/conversas", response_model=ConversaList)
async def listar_conversas(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    pool = get_pool()
    user_id = uuid.UUID(current_user["id"])
    rows = await conversas_q.listar_conversas(pool, user_id=user_id, limit=limit, offset=offset)
    data = [ConversaResponse(**dict(r)) for r in rows]
    return ConversaList(data=data)

@router.get("/conversas/{conversa_id}", response_model=ConversaDetail)
async def buscar_conversa(conversa_id: uuid.UUID, current_user: dict = Depends(get_current_user)):
    pool = get_pool()
    user_id = uuid.UUID(current_user["id"])
    result = await conversas_q.buscar_conversa(pool, conversa_id, user_id=user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return ConversaDetail(**result)

@router.post("/conversas/{conversa_id}/share")
async def compartilhar_conversa(conversa_id: uuid.UUID, current_user: dict = Depends(get_current_user)):
    pool = get_pool()
    user_id = uuid.UUID(current_user["id"])
    shared = await conversas_q.compartilhar_conversa(pool, conversa_id, user_id)
    if not shared:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return {"ok": True}

@router.get("/share/{conversa_id}", response_model=ConversaDetail)
async def buscar_conversa_publica(conversa_id: uuid.UUID):
    """Endpoint público — não exige autenticação."""
    pool = get_pool()
    result = await conversas_q.buscar_conversa_publica(pool, conversa_id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversa não encontrada ou não compartilhada")
    return ConversaDetail(**result)

@router.delete("/conversas/{conversa_id}")
async def deletar_conversa(conversa_id: uuid.UUID, current_user: dict = Depends(get_current_user)):
    pool = get_pool()
    user_id = uuid.UUID(current_user["id"])
    deleted = await conversas_q.deletar_conversa(pool, conversa_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return {"ok": True}

@router.delete("/conversas")
async def deletar_todas_conversas(current_user: dict = Depends(get_current_user)):
    """Delete every conversation belonging to the authenticated user. Idempotent."""
    pool = get_pool()
    user_id = uuid.UUID(current_user["id"])
    count = await conversas_q.deletar_todas_conversas(pool, user_id=user_id)
    return {"ok": True, "deleted": count}
