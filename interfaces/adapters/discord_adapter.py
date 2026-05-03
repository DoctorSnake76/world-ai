"""DiscordAdapter — canal Discord via Interactions API + REST.

Transport entrant : POST /webhook/discord (Interactions Webhook)
Envoi            : POST https://discord.com/api/v10/channels/{id}/messages
                   ou followup webhook pour les slash commands.

On utilise httpx directement (pas discord.py) pour garder le bundle léger
et rester cohérent avec le pattern stateless du gateway.

Slash commands (type=2), message components/boutons (type=3) et messages
directs de bot (type=0) sont supportés.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any

import httpx
import structlog

from interfaces.adapters.base_adapter import AdapterError, BaseAdapter
from interfaces.gateway.message import (
    ChannelType,
    ConfirmationChoice,
    UnifiedMessage,
)

logger = structlog.get_logger(__name__)

_DISCORD_API = "https://discord.com/api/v10"

# Interaction types Discord
_TYPE_PING = 1
_TYPE_APPLICATION_COMMAND = 2
_TYPE_MESSAGE_COMPONENT = 3

# Réponse types Discord
_RESP_PONG = 1
_RESP_CHANNEL_MESSAGE = 4
_RESP_DEFERRED_CHANNEL_MESSAGE = 5

# Mapping custom_id bouton → ConfirmationChoice
_CUSTOM_ID_TO_CHOICE: dict[str, ConfirmationChoice] = {
    "confirm": ConfirmationChoice.CONFIRM,
    "modify": ConfirmationChoice.MODIFY,
    "cancel": ConfirmationChoice.CANCEL,
}

_CONFIRM_LABELS: dict[ConfirmationChoice, str] = {
    ConfirmationChoice.CONFIRM: "Confirmer ✅",
    ConfirmationChoice.MODIFY: "Modifier ✏️",
    ConfirmationChoice.CANCEL: "Annuler ❌",
}

_CONFIRM_STYLE: dict[ConfirmationChoice, int] = {
    ConfirmationChoice.CONFIRM: 3,  # SUCCESS (green)
    ConfirmationChoice.MODIFY: 1,   # PRIMARY (blue)
    ConfirmationChoice.CANCEL: 4,   # DANGER (red)
}


class DiscordAdapter(BaseAdapter):
    """Adapter Discord — Interactions Webhook + REST API."""

    channel = ChannelType.DISCORD

    def __init__(
        self,
        token: str | None = None,
        app_id: str | None = None,
        public_key: str | None = None,
    ) -> None:
        self._token = token or os.environ.get("WORLDAI_DISCORD_BOT_TOKEN", "")
        self._app_id = app_id or os.environ.get("WORLDAI_DISCORD_APP_ID", "")
        self._public_key = public_key or os.environ.get("WORLDAI_DISCORD_PUBLIC_KEY", "")
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {}
            if self._token:
                headers["Authorization"] = f"Bot {self._token}"
            self._client = httpx.AsyncClient(
                base_url=_DISCORD_API,
                headers=headers,
                timeout=10.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Signature verification
    # ------------------------------------------------------------------

    def verify_signature(self, timestamp: str, body: str, signature: str) -> bool:
        """Vérifie la signature Ed25519 de Discord (nécessite PyNaCl ou cryptography).

        Si la bibliothèque n'est pas disponible, retourne True avec un log warning.
        """
        if not self._public_key:
            logger.warning("discord_no_public_key_configured")
            return True

        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            from cryptography.exceptions import InvalidSignature
            import binascii

            key_bytes = binascii.unhexlify(self._public_key)
            sig_bytes = binascii.unhexlify(signature)
            message = (timestamp + body).encode()
            pubkey = Ed25519PublicKey.from_public_bytes(key_bytes)
            try:
                pubkey.verify(sig_bytes, message)
                return True
            except InvalidSignature:
                return False
        except ImportError:
            logger.warning(
                "discord_sig_verify_skipped",
                reason="cryptography library not installed",
            )
            return True

    # ------------------------------------------------------------------
    # BaseAdapter — receive
    # ------------------------------------------------------------------

    async def receive(self, raw: dict[str, Any]) -> UnifiedMessage:
        """Parse un payload Interaction Discord en UnifiedMessage.

        Types supportés :
        - PING (type=1) → retourne un message système __ping__
        - APPLICATION_COMMAND (type=2) → slash command
        - MESSAGE_COMPONENT (type=3) → bouton inline (ConfirmationChoice)
        """
        interaction_type = raw.get("type", 0)

        if interaction_type == _TYPE_PING:
            return UnifiedMessage.text(
                channel=ChannelType.DISCORD,
                user_id="_system",
                session_id="_ping",
                content="__ping__",
                raw_payload=raw,
            )

        user_data = raw.get("member", {}).get("user", raw.get("user", {}))
        user_id = str(user_data.get("id", ""))
        guild_id = str(raw.get("guild_id", ""))
        channel_id = str(raw.get("channel_id", ""))
        session_id = f"{guild_id}:{channel_id}" if guild_id else channel_id

        metadata = {
            "interaction_id": raw.get("id"),
            "interaction_token": raw.get("token"),
            "guild_id": guild_id,
            "channel_id": channel_id,
            "app_id": raw.get("application_id", self._app_id),
        }

        if interaction_type == _TYPE_MESSAGE_COMPONENT:
            custom_id = raw.get("data", {}).get("custom_id", "")
            choice = _CUSTOM_ID_TO_CHOICE.get(custom_id)
            return UnifiedMessage(
                channel=ChannelType.DISCORD,
                user_id=user_id,
                session_id=session_id,
                content=custom_id,
                confirmation_choice=choice,
                raw_payload=raw,
                metadata=metadata,
            )

        if interaction_type == _TYPE_APPLICATION_COMMAND:
            options = raw.get("data", {}).get("options", [])
            content_parts = []
            for opt in options:
                if opt.get("type") == 3:  # STRING type
                    content_parts.append(str(opt.get("value", "")))
            content = " ".join(content_parts) if content_parts else raw.get("data", {}).get("name", "")
        else:
            content = raw.get("content", "")

        if not user_id:
            raise AdapterError("Discord payload missing user id")

        return UnifiedMessage(
            channel=ChannelType.DISCORD,
            user_id=user_id,
            session_id=session_id,
            content=content,
            raw_payload=raw,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # BaseAdapter — send
    # ------------------------------------------------------------------

    async def send(self, original: UnifiedMessage, response_text: str) -> None:
        """Envoie la réponse soit via followup interaction soit via channel messages."""
        interaction_token = original.metadata.get("interaction_token")
        app_id = original.metadata.get("app_id") or self._app_id

        if interaction_token and app_id:
            await self._send_interaction_followup(app_id, interaction_token, response_text)
        else:
            channel_id = original.metadata.get("channel_id") or original.session_id.split(":")[-1]
            if not channel_id:
                raise AdapterError("Cannot determine Discord channel_id for sending")
            await self._send_channel_message(channel_id, response_text)

        self._log("discord_sent", user_id=original.user_id)

    # ------------------------------------------------------------------
    # BaseAdapter — send_confirmation
    # ------------------------------------------------------------------

    async def send_confirmation(
        self,
        original: UnifiedMessage,
        prompt: str,
        choices: list[ConfirmationChoice] | None = None,
    ) -> None:
        """Envoie un message avec boutons de confirmation (components Discord)."""
        active_choices = choices or self.default_choices()
        components = [
            {
                "type": 1,  # ACTION_ROW
                "components": [
                    {
                        "type": 2,  # BUTTON
                        "style": _CONFIRM_STYLE[c],
                        "label": _CONFIRM_LABELS[c],
                        "custom_id": c.value,
                    }
                    for c in active_choices
                ],
            }
        ]

        interaction_token = original.metadata.get("interaction_token")
        app_id = original.metadata.get("app_id") or self._app_id

        payload: dict[str, Any] = {"content": prompt, "components": components}

        if interaction_token and app_id:
            await self._send_interaction_followup(app_id, interaction_token, "", extra=payload)
        else:
            channel_id = original.metadata.get("channel_id") or original.session_id.split(":")[-1]
            await self._call_api("POST", f"/channels/{channel_id}/messages", payload)

        self._log("discord_confirmation_sent", user_id=original.user_id)

    # ------------------------------------------------------------------
    # REST helpers
    # ------------------------------------------------------------------

    async def _send_channel_message(self, channel_id: str, content: str) -> None:
        await self._call_api("POST", f"/channels/{channel_id}/messages", {"content": content})

    async def _send_interaction_followup(
        self,
        app_id: str,
        token: str,
        content: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"content": content}
        if extra:
            payload.update(extra)
        url = f"/webhooks/{app_id}/{token}"
        await self._call_api("POST", url, payload)

    async def _call_api(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self._token:
            raise AdapterError("WORLDAI_DISCORD_BOT_TOKEN is not set")

        client = await self._get_client()
        try:
            if method == "POST":
                resp = await client.post(path, json=payload or {})
            else:
                resp = await client.get(path)
            resp.raise_for_status()
            if resp.content:
                return resp.json()
            return {}
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            logger.error(
                "discord_api_error",
                path=path,
                status=exc.response.status_code,
                body=body,
            )
            raise AdapterError(f"Discord API error {exc.response.status_code}: {body}") from exc
        except httpx.RequestError as exc:
            logger.error("discord_request_error", path=path, error=str(exc))
            raise AdapterError(f"Discord request failed: {exc}") from exc
