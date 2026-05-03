"""Gateway Multi-Canal — FastAPI port 8100.

Point d'entrée unique pour tous les canaux entrants.
Normalise chaque payload en UnifiedMessage, dispatche vers l'agent,
et renvoie la réponse formatée au canal d'origine.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from interfaces.adapters.base_adapter import AdapterError, BaseAdapter
from interfaces.gateway.message import ChannelType, UnifiedMessage
from interfaces.gateway.response_formatter import ResponseFormatter

logger = structlog.get_logger(__name__)

app = FastAPI(
    title="World AI — Gateway Multi-Canal",
    version="1.5.0",
    description="Normalise tous les canaux entrants en UnifiedMessage.",
)

_formatter = ResponseFormatter()

# ------------------------------------------------------------------
# Registre des adapters (peuplé via register_adapter)
# ------------------------------------------------------------------
_adapters: dict[ChannelType, BaseAdapter] = {}

# ------------------------------------------------------------------
# Dispatch callback vers le core agent (injecté au démarrage)
# ------------------------------------------------------------------
_agent_dispatch: Any = None  # callable(UnifiedMessage) -> str


def register_adapter(adapter: BaseAdapter) -> None:
    """Enregistre un adapter pour son canal."""
    _adapters[adapter.channel] = adapter
    logger.info("adapter_registered", channel=adapter.channel.value)


def set_agent_dispatch(fn: Any) -> None:
    """Injecte le callback vers l'agent (évite l'import circulaire)."""
    global _agent_dispatch
    _agent_dispatch = fn


def get_adapter(channel: ChannelType) -> BaseAdapter:
    adapter = _adapters.get(channel)
    if adapter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No adapter registered for channel '{channel.value}'",
        )
    return adapter


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "gateway"}


@app.get("/channels")
async def list_channels() -> dict[str, list[str]]:
    """Retourne la liste des canaux enregistrés."""
    return {"channels": [ch.value for ch in _adapters]}


@app.post("/webhook/{channel}")
async def webhook(channel: str, request: Request) -> JSONResponse:
    """Reçoit un webhook brut, normalise, dispatch, renvoie la réponse."""
    try:
        ch = ChannelType(channel)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown channel '{channel}'",
        )

    adapter = get_adapter(ch)

    try:
        raw = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JSON body",
        )

    try:
        unified: UnifiedMessage = await adapter.receive(raw)
    except AdapterError as exc:
        logger.error("adapter_receive_error", channel=channel, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    response_text = await _dispatch_to_agent(unified)

    formatted = _formatter.format(response_text, ch)

    try:
        await adapter.send(unified, formatted)
    except AdapterError as exc:
        logger.error("adapter_send_error", channel=channel, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to send response: {exc}",
        )

    logger.info(
        "webhook_handled",
        channel=channel,
        user_id=unified.user_id,
        session_id=unified.session_id,
    )
    return JSONResponse({"status": "ok", "channel": channel})


@app.post("/message")
async def post_message(body: dict[str, Any]) -> dict[str, str]:
    """Endpoint direct (REST) — reçoit un UnifiedMessage pré-normalisé.

    Utile pour les adapters qui gèrent eux-mêmes le transport
    (ex : voice adapter) et n'ont pas besoin du webhook générique.
    """
    try:
        unified = UnifiedMessage(**body)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    response_text = await _dispatch_to_agent(unified)
    formatted = _formatter.format(response_text, unified.channel)

    return {"response": formatted, "channel": unified.channel.value}


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


async def _dispatch_to_agent(msg: UnifiedMessage) -> str:
    """Appelle le callback agent ou renvoie un stub si non configuré."""
    if _agent_dispatch is None:
        logger.warning("agent_dispatch_not_configured", user_id=msg.user_id)
        return f"[Gateway] Agent not configured — received: {msg.content}"

    result = _agent_dispatch(msg)
    # Support sync et async callables
    if hasattr(result, "__await__"):
        return await result
    return result
