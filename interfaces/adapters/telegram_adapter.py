"""TelegramAdapter — canal Telegram via API Bot REST.

Transport : webhook HTTP entrant → /webhook/telegram
Envoi     : POST https://api.telegram.org/bot{TOKEN}/sendMessage

Pas de dépendance à python-telegram-bot — utilise httpx async directement
pour garder le bundle léger et sans état (aucun polling thread).
Les boutons inline pour les confirmations utilisent InlineKeyboardMarkup.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog

from interfaces.adapters.base_adapter import AdapterError, BaseAdapter
from interfaces.gateway.message import (
    Attachment,
    AttachmentType,
    ChannelType,
    ConfirmationChoice,
    UnifiedMessage,
)

logger = structlog.get_logger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

_CONFIRM_LABELS: dict[ConfirmationChoice, str] = {
    ConfirmationChoice.CONFIRM: "Confirmer ✅",
    ConfirmationChoice.MODIFY: "Modifier ✏️",
    ConfirmationChoice.CANCEL: "Annuler ❌",
}

_CONFIRM_DATA: dict[ConfirmationChoice, str] = {
    ConfirmationChoice.CONFIRM: "confirm",
    ConfirmationChoice.MODIFY: "modify",
    ConfirmationChoice.CANCEL: "cancel",
}

# Callback data → ConfirmationChoice (used when parsing callback_query)
_DATA_TO_CHOICE: dict[str, ConfirmationChoice] = {
    v: k for k, v in _CONFIRM_DATA.items()
}


class TelegramAdapter(BaseAdapter):
    """Adapter Telegram — webhook entrant + réponse via Bot API REST."""

    channel = ChannelType.TELEGRAM

    def __init__(self, token: str | None = None) -> None:
        self._token = token or os.environ.get("WORLDAI_TELEGRAM_BOT_TOKEN", "")
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # BaseAdapter — receive
    # ------------------------------------------------------------------

    async def receive(self, raw: dict[str, Any]) -> UnifiedMessage:
        """Parse un Update Telegram en UnifiedMessage.

        Supporte :
        - message.text (texte simple)
        - message.voice / audio (attachment audio)
        - message.document / photo (attachment fichier/image)
        - callback_query (réponse bouton inline → ConfirmationChoice)
        """
        # -- callback_query (bouton inline pressé) --
        if "callback_query" in raw:
            return self._parse_callback_query(raw["callback_query"])

        message = raw.get("message") or raw.get("edited_message")
        if not message:
            raise AdapterError("Unsupported Telegram update: no message or callback_query")

        chat_id = str(message.get("chat", {}).get("id", ""))
        user = message.get("from", {})
        user_id = str(user.get("id", chat_id))
        session_id = chat_id  # un chat = une session

        # -- texte --
        text: str = message.get("text", message.get("caption", ""))

        # -- pièces jointes --
        attachments: list[Attachment] = []
        if "voice" in message:
            attachments.append(self._tg_file_to_attachment(message["voice"], AttachmentType.AUDIO))
        if "audio" in message:
            attachments.append(self._tg_file_to_attachment(message["audio"], AttachmentType.AUDIO))
        if "document" in message:
            attachments.append(self._tg_file_to_attachment(message["document"], AttachmentType.DOCUMENT))
        if "photo" in message:
            # Telegram renvoie plusieurs tailles — on prend la plus grande
            largest = max(message["photo"], key=lambda p: p.get("file_size", 0))
            attachments.append(self._tg_file_to_attachment(largest, AttachmentType.IMAGE))

        return UnifiedMessage(
            channel=ChannelType.TELEGRAM,
            user_id=user_id,
            session_id=session_id,
            content=text,
            attachments=attachments,
            raw_payload=raw,
        )

    # ------------------------------------------------------------------
    # BaseAdapter — send
    # ------------------------------------------------------------------

    async def send(self, original: UnifiedMessage, response_text: str) -> None:
        """Envoie un message texte Markdown V2 sur le chat d'origine."""
        if not self._token:
            self._log_error("telegram_token_missing")
            raise AdapterError("WORLDAI_TELEGRAM_BOT_TOKEN is not set")

        chat_id = original.session_id
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": response_text,
            "parse_mode": "MarkdownV2",
        }

        await self._call_api("sendMessage", payload)
        self._log("telegram_sent", chat_id=chat_id)

    # ------------------------------------------------------------------
    # BaseAdapter — send_confirmation
    # ------------------------------------------------------------------

    async def send_confirmation(
        self,
        original: UnifiedMessage,
        prompt: str,
        choices: list[ConfirmationChoice] | None = None,
    ) -> None:
        """Envoie un gate de confirmation avec boutons inline Telegram."""
        if not self._token:
            raise AdapterError("WORLDAI_TELEGRAM_BOT_TOKEN is not set")

        active_choices = choices or self.default_choices()
        keyboard = [
            [{"text": _CONFIRM_LABELS[c], "callback_data": _CONFIRM_DATA[c]}]
            for c in active_choices
        ]

        payload: dict[str, Any] = {
            "chat_id": original.session_id,
            "text": prompt,
            "parse_mode": "MarkdownV2",
            "reply_markup": {"inline_keyboard": keyboard},
        }

        await self._call_api("sendMessage", payload)
        self._log("telegram_confirmation_sent", chat_id=original.session_id)

    # ------------------------------------------------------------------
    # Helpers internes
    # ------------------------------------------------------------------

    def _parse_callback_query(self, cq: dict[str, Any]) -> UnifiedMessage:
        user = cq.get("from", {})
        user_id = str(user.get("id", ""))
        chat_id = str(cq.get("message", {}).get("chat", {}).get("id", user_id))
        data = cq.get("data", "")
        choice = _DATA_TO_CHOICE.get(data)

        return UnifiedMessage(
            channel=ChannelType.TELEGRAM,
            user_id=user_id,
            session_id=chat_id,
            content=data,
            confirmation_choice=choice,
            raw_payload={"callback_query": cq},
        )

    @staticmethod
    def _tg_file_to_attachment(
        tg_file: dict[str, Any], att_type: AttachmentType
    ) -> Attachment:
        return Attachment(
            attachment_type=att_type,
            filename=tg_file.get("file_name"),
            mime_type=tg_file.get("mime_type"),
            size_bytes=tg_file.get("file_size"),
            metadata={"file_id": tg_file.get("file_id")},
        )

    async def _call_api(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = _TELEGRAM_API.format(token=self._token, method=method)
        client = await self._get_client()
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            logger.error("telegram_api_error", method=method, status=exc.response.status_code, body=body)
            raise AdapterError(f"Telegram API error {exc.response.status_code}: {body}") from exc
        except httpx.RequestError as exc:
            logger.error("telegram_request_error", method=method, error=str(exc))
            raise AdapterError(f"Telegram request failed: {exc}") from exc
