"""Stream de eventos do agente Calunga para o frontend via SSE.

Protocolo (cada evento e um JSON serializado):
- text          : chunk de texto da resposta final. Content e concatenado.
- tool_start    : {tool, args}. Frontend mostra "buscando X com Y".
- tool_end      : {tool, status, preview?|error?}. Status 'ok' ou 'error'.
- error         : erro geral do stream (antes do [DONE] final).
- [DONE]        : sinaliza fim do stream. Emitido em qualquer caso (sucesso
                  ou erro) para o Vercel AI SDK saber que acabou.
"""

import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import AIMessageChunk

from app.metrics import incr_by_dim, observe_ms

logger = logging.getLogger(__name__)

_PREVIEW_MAX_CHARS = 280
_ARGS_MAX_CHARS = 400

def _safe_json(value: Any, max_chars: int) -> str:
    """Serializa valor para JSON truncando a uma janela razoavel."""
    try:
        s = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        s = str(value)
    return s if len(s) <= max_chars else s[:max_chars] + "..."

def _extract_args(event: dict) -> dict | str:
    """Extrai os argumentos de input de uma tool do evento do LangGraph."""
    data = event.get("data") or {}
    inp = data.get("input")
    if inp is None:
        return {}
    if isinstance(inp, dict):

        if "args" in inp and isinstance(inp["args"], dict):
            return inp["args"]
        if "input" in inp and isinstance(inp["input"], dict):
            return inp["input"]
        return inp
    return str(inp)

def _extract_output_preview(event: dict) -> tuple[str, str | None]:
    """Retorna (status, preview_ou_erro).

    Status 'ok' quando a tool retornou normalmente, 'error' quando levantou.
    """
    data = event.get("data") or {}
    output = data.get("output")
    if output is None:
        return "ok", None

    if hasattr(output, "content"):
        output = output.content
    text = output if isinstance(output, str) else _safe_json(output, _PREVIEW_MAX_CHARS)

    if isinstance(text, str) and '"modo": "erro"' in text[:60]:
        return "error", text[:_PREVIEW_MAX_CHARS]
    return "ok", text[:_PREVIEW_MAX_CHARS] if isinstance(text, str) else None

async def stream_agent_response(
    agent,
    messages: list[dict],
    config: dict | None = None,
) -> AsyncGenerator[dict, None]:
    """Stream agent response as SSE events compatible with Vercel AI SDK."""
    tool_start_times: dict[str, float] = {}
    try:
        async for event in agent.astream_events(
            {"messages": messages},
            version="v2",
            config=config or {},
        ):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    if isinstance(chunk.content, str):
                        yield {"data": json.dumps({"type": "text", "content": chunk.content})}
                    elif isinstance(chunk.content, list):
                        for block in chunk.content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                yield {"data": json.dumps({"type": "text", "content": block["text"]})}

            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                args = _extract_args(event)
                tool_start_times[tool_name] = time.perf_counter()
                await incr_by_dim("tool.calls", tool_name)
                payload = {
                    "type": "tool_start",
                    "tool": tool_name,
                    "args": args if isinstance(args, dict) else {"raw": args},
                }
                logger.info("tool_start name=%s args=%s", tool_name, _safe_json(args, _ARGS_MAX_CHARS))
                yield {"data": json.dumps(payload, ensure_ascii=False)}

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                status, preview = _extract_output_preview(event)
                started = tool_start_times.pop(tool_name, None)
                if started is not None:
                    ms = int((time.perf_counter() - started) * 1000)
                    await observe_ms(f"tool.latency.{tool_name}", ms)
                if status == "error":
                    await incr_by_dim("tool.errors", tool_name)
                payload: dict = {"type": "tool_end", "tool": tool_name, "status": status}
                if status == "error" and preview:
                    payload["error"] = preview
                elif preview:
                    payload["preview"] = preview
                logger.info("tool_end name=%s status=%s", tool_name, status)
                yield {"data": json.dumps(payload, ensure_ascii=False)}

            elif kind == "on_tool_error":
                tool_name = event.get("name", "unknown")
                err = (event.get("data") or {}).get("error") or event.get("error")
                err_text = str(err) if err else "erro desconhecido"
                tool_start_times.pop(tool_name, None)
                await incr_by_dim("tool.errors", tool_name)
                logger.warning("tool_error name=%s err=%s", tool_name, err_text)
                yield {"data": json.dumps({
                    "type": "tool_end",
                    "tool": tool_name,
                    "status": "error",
                    "error": err_text[:_PREVIEW_MAX_CHARS],
                }, ensure_ascii=False)}

        yield {"data": "[DONE]"}

    except Exception as e:
        logger.exception("Error streaming agent response")
        yield {"data": json.dumps({"type": "error", "content": str(e)})}
        yield {"data": "[DONE]"}
