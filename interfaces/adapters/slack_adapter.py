"""SlackAdapter — canal Slack via Events API + Web API.

Transport entrant : POST /webhook/slack (Slack Events API)
Envoi            : POST https://slack.com/api/chat.postMessage

Pas de dépendance à slack-bolt — on utilise httpx directement.
La vérification de signature HMAC-SHA256 est incluse (stdlib).

Supporte :
- url_verification challenge (onboarding Slack)
- event_callback : message, app_mention, slash_command responses
- block_actions (boutons de confirmation)
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

_SLACK_API = "https://slack.com/api"

_CONFIRM_LABELS: dict[ConfirmationChoice, str] = {
    ConfirmationChoice.CONFIRM: "Confirmer ✅",
    ConfirmationChoice.MODIFY: "Modifier ✏️",
    ConfirmationChoice.CANCEL: "Annuler ❌",
}

_CONFIRM_STYLE: dict[ConfirmationChoice, str] = {
    ConfirmationChoice.CONFIRM: "primary",
    ConfirmationChoice.MODIFY: "default",
    ConfirmationChoice.CANCEL: "danger",
}

_ACTION_ID_TO_CHOICE: dict[str, ConfirmationChoice] = {
    "confirm": ConfirmationChoice.CONFIRM,
    "modify": ConfirmationChoice.MODIFY,
    "cancel": ConfirmationChoice.CANCEL,
}

_SLACK_SIGNATURE_VERSION = "v0"
_SIGNATURE_VALIDITY_SECONDS = 300


class SlackAdapter(BaseAdapter):
    """Adapter Slack — Events API + Web API REST."""

    channel = ChannelType.SLACK

    def __init__(
        self,
        bot_token: str | None = None,
        signing_secret: str | None = None,
    ) -> None:
        self._bot_token = bot_token or os.environ.get("WORLDAI_SLACK_BOT_TOKEN", "")
        self._signing_secret = signing_secret or os.environ.get(
            "WORLDAI_SLACK_SIGNING_SECRET", ""
        )
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=_SLACK_API,
                headers={"Authorization": f"Bearer {self._bot_token}"},
                timeout=10.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Signature verification
    # ------------------------------------------------------------------

    def verify_signature(
        self,
        timestamp: str,
        raw_body: str | bytes,
        slack_signature: str,
    ) -> bool:
        """Vérifie la signature HMAC-SHA256 Slack (stdlib hmac)."""
        if not self._signing_secret:
            logger.warning("slack_no_signing_secret")
            return True

        try:
            ts = int(timestamp)
        except (ValueError, TypeError):
            return False

        if abs(time.time() - ts) > _SIGNATURE_VALIDITY_SECONDS:
            logger.warning("slack_signature_expired", timestamp=timestamp)
            return False

        body_str = raw_body if isinstance(raw_body, str) else raw_body.decode()
        base = f"{_SLACK_SIGNATURE_VERSION}:{timestamp}:{body_str}"
        expected = (
            _SLACK_SIGNATURE_VERSION
            + "="
            + hmac.new(
                self._signing_secret.encode(),
                base.encode(),
                hashlib.sha256,
            ).hexdigest()
        )
        return hmac.compare_digest(expected, slack_signature)

    # ------------------------------------------------------------------
    # BaseAdapter — receive
    # ------------------------------------------------------------------

    async def receive(self, raw: dict[str, Any]) -> UnifiedMessage:
        """Parse le payload Slack Events API en UnifiedMessage.

        Supporte :
        - url_verification challenge → retourne un message système __challenge__
        - event_callback:message (message normal ou app_mention)
        - block_actions (bouton de confirmation)
        """
        event_type = raw.get("type", "")

        # -- URL Verification challenge --
        if event_type == "url_verification":
            return UnifiedMessage.text(
                channel=ChannelType.SLACK,
                user_id="_system",
                session_id="_challenge",
                content=f"__challenge__:{raw.get('challenge', '')}",
                raw_payload=raw,
            )

        # -- Block actions (boutons) --
        if event_type == "block_actions":
            return self._parse_block_action(raw)

        # -- Event callback (messages) --
        if event_type == "event_callback":
            return self._parse_event_callback(raw)

        raise AdapterError(f"Unsupported Slack event type: '{event_type}'")

    # ------------------------------------------------------------------
    # BaseAdapter — send
    # ------------------------------------------------------------------

    async def send(self, original: UnifiedMessage, response_text: str) -> None:
        """Envoie un message via chat.postMessage."""
        if not self._bot_token:
            raise AdapterError("WORLDAI_SLACK_BOT_TOKEN is not set")

        channel = original.metadata.get("slack_channel") or original.session_id

        payload: dict[str, Any] = {
            "channel": channel,
            "text": response_text,
            "mrkdwn": True,
        }

        # Thread reply si reply_to est défini
        if original.reply_to:
            payload["thread_ts"] = original.reply_to

        await self._call_api("/chat.postMessage", payload)
        self._log("slack_sent", slack_channel=channel)

    # ------------------------------------------------------------------
    # BaseAdapter — send_confirmation
    # ------------------------------------------------------------------

    async def send_confirmation(
        self,
        original: UnifiedMessage,
        prompt: str,
        choices: list[ConfirmationChoice] | None = None,
    ) -> None:
        """Envoie un message Slack avec Block Kit buttons."""
        if not self._bot_token:
            raise AdapterError("WORLDAI_SLACK_BOT_TOKEN is not set")

        active_choices = choices or self.default_choices()
        channel = original.metadata.get("slack_channel") or original.session_id

        elements = [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": _CONFIRM_LABELS[c]},
                "action_id": c.value,
                "style": _CONFIRM_STYLE[c],
            }
            for c in active_choices
        ]

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": prompt}},
            {"type": "actions", "elements": elements},
        ]

        payload: dict[str, Any] = {
            "channel": channel,
            "text": prompt,
            "blocks": blocks,
        }

        if original.reply_to:
            payload["thread_ts"] = original.reply_to

        await self._call_api("/chat.postMessage", payload)
        self._log("slack_confirmation_sent", slack_channel=channel)

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse_event_callback(self, raw: dict[str, Any]) -> UnifiedMessage:
        event = raw.get("event", {})
        event_sub_type = event.get("type", "")

        if event_sub_type not in ("message", "app_mention"):
            raise AdapterError(f"Unsupported Slack event sub-type: '{event_sub_type}'")

        # Ignorer les messages de bots (pour éviter les boucles)
        if event.get("bot_id") or event.get("subtype"):
            raise AdapterError("Slack bot message or subtype message — ignoring")

        user_id = str(event.get("user", ""))
        channel_id = str(event.get("channel", ""))
        thread_ts = event.get("thread_ts") or event.get("ts")

        return UnifiedMessage(
            channel=ChannelType.SLACK,
            user_id=user_id,
            session_id=channel_id,
            content=event.get("text", ""),
            reply_to=thread_ts,
            raw_payload=raw,
            metadata={"slack_channel": channel_id, "event_ts": event.get("ts")},
        )

    def _parse_block_action(self, raw: dict[str, Any]) -> UnifiedMessage:
        user = raw.get("user", {})
        user_id = str(user.get("id", ""))
        channel = raw.get("channel", {})
        channel_id = str(channel.get("id", ""))
        container = raw.get("container", {})
        thread_ts = container.get("thread_ts") or container.get("message_ts")

        actions = raw.get("actions", [])
        if not actions:
            raise AdapterError("Slack block_actions: no actions in payload")

        action = actions[0]
        action_id = action.get("action_id", "")
        choice = _ACTION_ID_TO_CHOICE.get(action_id)

        return UnifiedMessage(
            channel=ChannelType.SLACK,
            user_id=user_id,
            session_id=channel_id,
            content=action_id,
            confirmation_choice=choice,
            reply_to=thread_ts,
            raw_payload=raw,
            metadata={"slack_channel": channel_id},
        )

    # ------------------------------------------------------------------
    # REST helper
    # ------------------------------------------------------------------

    async def _call_api(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        client = await self._get_client()
        try:
            resp = await client.post(path, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                error = data.get("error", "unknown")
                raise AdapterError(f"Slack API returned error: {error}")
            return data
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            logger.error("slack_api_error", path=path, status=exc.response.status_code, body=body)
            raise AdapterError(f"Slack API HTTP error {exc.response.status_code}: {body}") from exc
        except httpx.RequestError as exc:
            logger.error("slack_request_error", path=path, error=str(exc))
            raise AdapterError(f"Slack request failed: {exc}") from exc
