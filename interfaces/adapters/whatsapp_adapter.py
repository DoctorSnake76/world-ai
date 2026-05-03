"""WhatsAppAdapter — canal WhatsApp via Twilio API.

Transport entrant : POST /webhook/whatsapp (Twilio Status Callback)
Envoi            : POST https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json

Note : Twilio envoie les webhooks en application/x-www-form-urlencoded,
pas en JSON. Le gateway doit passer le payload déjà parsé sous forme de dict
(les clés Twilio telles quelles). Le endpoint /webhook/whatsapp devrait
utiliser request.form() et non request.json().

Mode WORLDAI_WHATSAPP_MODE=twilio (défaut) | web (stub, Phase 2).
"""

from __future__ import annotations

import base64
import os
from typing import Any
from urllib.parse import urlencode

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

_TWILIO_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

_CONFIRM_LABELS: dict[ConfirmationChoice, str] = {
    ConfirmationChoice.CONFIRM: "1 - Confirmer",
    ConfirmationChoice.MODIFY: "2 - Modifier",
    ConfirmationChoice.CANCEL: "3 - Annuler",
}

# Mapping réponse texte → ConfirmationChoice (lecture réponse utilisateur)
_TEXT_TO_CHOICE: dict[str, ConfirmationChoice] = {
    "1": ConfirmationChoice.CONFIRM,
    "confirmer": ConfirmationChoice.CONFIRM,
    "confirm": ConfirmationChoice.CONFIRM,
    "oui": ConfirmationChoice.CONFIRM,
    "yes": ConfirmationChoice.CONFIRM,
    "2": ConfirmationChoice.MODIFY,
    "modifier": ConfirmationChoice.MODIFY,
    "modify": ConfirmationChoice.MODIFY,
    "3": ConfirmationChoice.CANCEL,
    "annuler": ConfirmationChoice.CANCEL,
    "cancel": ConfirmationChoice.CANCEL,
    "non": ConfirmationChoice.CANCEL,
    "no": ConfirmationChoice.CANCEL,
}


def _detect_confirmation(text: str) -> ConfirmationChoice | None:
    return _TEXT_TO_CHOICE.get(text.strip().lower())


class WhatsAppAdapter(BaseAdapter):
    """Adapter WhatsApp — Twilio Messaging API."""

    channel = ChannelType.WHATSAPP

    def __init__(
        self,
        account_sid: str | None = None,
        auth_token: str | None = None,
        whatsapp_number: str | None = None,
    ) -> None:
        self._account_sid = account_sid or os.environ.get("WORLDAI_TWILIO_ACCOUNT_SID", "")
        self._auth_token = auth_token or os.environ.get("WORLDAI_TWILIO_AUTH_TOKEN", "")
        self._whatsapp_number = whatsapp_number or os.environ.get(
            "WORLDAI_TWILIO_WHATSAPP_NUMBER", ""
        )
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            creds = base64.b64encode(
                f"{self._account_sid}:{self._auth_token}".encode()
            ).decode()
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Basic {creds}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=10.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # BaseAdapter — receive
    # ------------------------------------------------------------------

    async def receive(self, raw: dict[str, Any]) -> UnifiedMessage:
        """Parse le payload Twilio WhatsApp (form-data parsé) en UnifiedMessage.

        Les clés Twilio typiques :
        - From        : "whatsapp:+33612345678"
        - To          : "whatsapp:+14155238886"
        - Body        : texte du message
        - NumMedia    : nombre de médias attachés
        - MediaUrl0   : URL premier media
        - MediaContentType0 : content-type premier media
        - WaId        : identifiant WhatsApp (sans le "whatsapp:" prefix)
        """
        body = raw.get("Body", "")
        from_number = raw.get("From", "")
        wa_id = raw.get("WaId", "")

        if not from_number:
            raise AdapterError("WhatsApp payload missing 'From' field")

        user_id = wa_id or from_number.replace("whatsapp:", "")
        session_id = user_id

        # Détection de confirmation par texte libre
        choice = _detect_confirmation(body)

        # Médias attachés (images, documents, audio)
        attachments: list[Attachment] = []
        num_media = int(raw.get("NumMedia", 0))
        for i in range(num_media):
            media_url = raw.get(f"MediaUrl{i}")
            content_type = raw.get(f"MediaContentType{i}", "application/octet-stream")
            if media_url:
                if content_type.startswith("image/"):
                    att_type = AttachmentType.IMAGE
                elif content_type.startswith("audio/"):
                    att_type = AttachmentType.AUDIO
                elif content_type.startswith("video/"):
                    att_type = AttachmentType.VIDEO
                else:
                    att_type = AttachmentType.DOCUMENT
                attachments.append(
                    Attachment(
                        attachment_type=att_type,
                        url=media_url,
                        mime_type=content_type,
                    )
                )

        return UnifiedMessage(
            channel=ChannelType.WHATSAPP,
            user_id=user_id,
            session_id=session_id,
            content=body,
            attachments=attachments,
            confirmation_choice=choice,
            raw_payload=raw,
            metadata={"from_number": from_number, "to_number": raw.get("To", "")},
        )

    # ------------------------------------------------------------------
    # BaseAdapter — send
    # ------------------------------------------------------------------

    async def send(self, original: UnifiedMessage, response_text: str) -> None:
        """Envoie un message WhatsApp via Twilio REST API."""
        if not self._account_sid or not self._auth_token:
            raise AdapterError("WORLDAI_TWILIO_ACCOUNT_SID or AUTH_TOKEN is not set")
        if not self._whatsapp_number:
            raise AdapterError("WORLDAI_TWILIO_WHATSAPP_NUMBER is not set")

        to_number = original.metadata.get("from_number") or f"whatsapp:{original.user_id}"
        if not to_number.startswith("whatsapp:"):
            to_number = f"whatsapp:{to_number}"

        from_number = self._whatsapp_number
        if not from_number.startswith("whatsapp:"):
            from_number = f"whatsapp:{from_number}"

        payload = {"To": to_number, "From": from_number, "Body": response_text}
        await self._call_api(payload)
        self._log("whatsapp_sent", to=to_number)

    # ------------------------------------------------------------------
    # BaseAdapter — send_confirmation
    # ------------------------------------------------------------------

    async def send_confirmation(
        self,
        original: UnifiedMessage,
        prompt: str,
        choices: list[ConfirmationChoice] | None = None,
    ) -> None:
        """Envoie un message texte listé avec les choix numérotés."""
        active_choices = choices or self.default_choices()
        options_text = "\n".join(_CONFIRM_LABELS[c] for c in active_choices)
        full_text = f"{prompt}\n\n{options_text}"
        await self.send(original, full_text)

    # ------------------------------------------------------------------
    # REST helper
    # ------------------------------------------------------------------

    async def _call_api(self, form_data: dict[str, str]) -> dict[str, Any]:
        url = _TWILIO_API.format(sid=self._account_sid)
        client = await self._get_client()
        try:
            resp = await client.post(url, content=urlencode(form_data).encode())
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            logger.error(
                "whatsapp_api_error",
                status=exc.response.status_code,
                body=body,
            )
            raise AdapterError(
                f"Twilio API error {exc.response.status_code}: {body}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("whatsapp_request_error", error=str(exc))
            raise AdapterError(f"Twilio request failed: {exc}") from exc
