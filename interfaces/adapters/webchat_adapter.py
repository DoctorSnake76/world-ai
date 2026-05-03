"""WebChatAdapter — canal Web Chat via WebSocket (port 8101).

Architecture :
- Serveur WebSocket FastAPI sur port 8101
- Chaque connexion WebSocket = une session (session_id = UUID)
- Protocol JSON bidirectionnel :
    entrant  → {"user_id": "...", "content": "...", "session_id": "..."}
    sortant  → {"type": "message", "content": "...", "session_id": "..."}
    confirmation → {"type": "confirmation", "prompt": "...", "choices": [...]}

La méthode receive() est appelée avec le payload JSON parsé depuis le WebSocket.
La méthode send() envoie la réponse à la connexion WebSocket active.
Les connexions actives sont stockées dans un registre thread-safe (asyncio).

Pour intégrer dans gateway.py :
    from interfaces.adapters.webchat_adapter import WebChatAdapter, webchat_app
    # Mount webchat_app sur le port 8101 séparément
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import structlog

from interfaces.adapters.base_adapter import AdapterError, BaseAdapter
from interfaces.gateway.message import (
    ChannelType,
    ConfirmationChoice,
    UnifiedMessage,
)

logger = structlog.get_logger(__name__)

_CONFIRM_LABELS: dict[ConfirmationChoice, str] = {
    ConfirmationChoice.CONFIRM: "Confirmer ✅",
    ConfirmationChoice.MODIFY: "Modifier ✏️",
    ConfirmationChoice.CANCEL: "Annuler ❌",
}

# Registre global des connexions WebSocket actives
# session_id → connexion WebSocket (objet avec méthode send_json)
_active_connections: dict[str, Any] = {}


def register_connection(session_id: str, ws: Any) -> None:
    """Enregistre une connexion WebSocket active."""
    _active_connections[session_id] = ws
    logger.info("webchat_connection_registered", session_id=session_id)


def unregister_connection(session_id: str) -> None:
    """Supprime une connexion WebSocket (déconnexion)."""
    _active_connections.pop(session_id, None)
    logger.info("webchat_connection_removed", session_id=session_id)


def get_connection(session_id: str) -> Any | None:
    return _active_connections.get(session_id)


def list_active_sessions() -> list[str]:
    return list(_active_connections.keys())


class WebChatAdapter(BaseAdapter):
    """Adapter Web Chat — WebSocket JSON bidirectionnel."""

    channel = ChannelType.WEBCHAT

    def __init__(self, jwt_secret: str | None = None) -> None:
        self._jwt_secret = jwt_secret or os.environ.get("WORLDAI_WEBCHAT_SECRET", "")

    # ------------------------------------------------------------------
    # BaseAdapter — receive
    # ------------------------------------------------------------------

    async def receive(self, raw: dict[str, Any]) -> UnifiedMessage:
        """Parse un payload JSON WebSocket en UnifiedMessage.

        Format attendu :
        {
            "user_id": "...",           # identifiant utilisateur (requis)
            "content": "...",           # texte du message
            "session_id": "...",        # session existante ou absent → génère UUID
            "choice": "confirm"|"modify"|"cancel"  # optionnel (confirmation)
        }
        """
        user_id = raw.get("user_id", "")
        if not user_id:
            raise AdapterError("WebChat payload missing 'user_id'")

        content = raw.get("content", "")
        session_id = raw.get("session_id") or str(uuid.uuid4())

        # Détection d'une réponse de confirmation
        choice_str = raw.get("choice", "")
        choice: ConfirmationChoice | None = None
        if choice_str:
            try:
                choice = ConfirmationChoice(choice_str.lower())
            except ValueError:
                choice = None

        return UnifiedMessage(
            channel=ChannelType.WEBCHAT,
            user_id=user_id,
            session_id=session_id,
            content=content,
            confirmation_choice=choice,
            raw_payload=raw,
            metadata={"origin": "websocket"},
        )

    # ------------------------------------------------------------------
    # BaseAdapter — send
    # ------------------------------------------------------------------

    async def send(self, original: UnifiedMessage, response_text: str) -> None:
        """Envoie la réponse JSON à la connexion WebSocket active.

        Si la connexion n'est plus active, log un warning et ne lève pas.
        """
        ws = get_connection(original.session_id)
        if ws is None:
            logger.warning(
                "webchat_no_active_connection",
                session_id=original.session_id,
            )
            return

        payload: dict[str, Any] = {
            "type": "message",
            "session_id": original.session_id,
            "content": response_text,
        }

        try:
            await ws.send_json(payload)
            self._log("webchat_sent", session_id=original.session_id)
        except Exception as exc:
            logger.error("webchat_send_error", session_id=original.session_id, error=str(exc))
            unregister_connection(original.session_id)
            raise AdapterError(f"WebSocket send failed: {exc}") from exc

    # ------------------------------------------------------------------
    # BaseAdapter — send_confirmation
    # ------------------------------------------------------------------

    async def send_confirmation(
        self,
        original: UnifiedMessage,
        prompt: str,
        choices: list[ConfirmationChoice] | None = None,
    ) -> None:
        """Envoie un payload de confirmation avec les choix disponibles."""
        active_choices = choices or self.default_choices()
        ws = get_connection(original.session_id)
        if ws is None:
            logger.warning(
                "webchat_no_active_connection",
                session_id=original.session_id,
            )
            return

        payload: dict[str, Any] = {
            "type": "confirmation",
            "session_id": original.session_id,
            "prompt": prompt,
            "choices": [
                {"id": c.value, "label": _CONFIRM_LABELS[c]} for c in active_choices
            ],
        }

        try:
            await ws.send_json(payload)
            self._log("webchat_confirmation_sent", session_id=original.session_id)
        except Exception as exc:
            logger.error(
                "webchat_confirmation_error",
                session_id=original.session_id,
                error=str(exc),
            )
            unregister_connection(original.session_id)
            raise AdapterError(f"WebSocket confirmation send failed: {exc}") from exc

    # ------------------------------------------------------------------
    # WebSocket lifecycle helpers (appelés depuis le handler WebSocket)
    # ------------------------------------------------------------------

    def on_connect(self, session_id: str, ws: Any) -> None:
        """À appeler lors d'une nouvelle connexion WebSocket."""
        register_connection(session_id, ws)

    def on_disconnect(self, session_id: str) -> None:
        """À appeler lors d'une déconnexion WebSocket."""
        unregister_connection(session_id)
