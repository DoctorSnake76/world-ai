"""EmailAdapter — canal Email via IMAP (entrant) + SMTP (sortant).

Transport entrant : polling IMAP asynchrone (asyncio.run_in_executor)
Envoi            : SMTP via smtplib (stdlib, wrappé en executor)

Utilise uniquement la bibliothèque standard Python (imaplib, smtplib, email)
pour éviter des dépendances lourdes en Phase 1.

Le polling IMAP est lancé en tâche de fond via start_polling().
Chaque email non-vu est converti en UnifiedMessage et transmis au callback.
"""

from __future__ import annotations

import asyncio
import email as email_lib
import email.header
import email.utils
import imaplib
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Callable, Awaitable

import structlog

from interfaces.adapters.base_adapter import AdapterError, BaseAdapter
from interfaces.gateway.message import (
    AttachmentType,
    Attachment,
    ChannelType,
    ConfirmationChoice,
    UnifiedMessage,
)

logger = structlog.get_logger(__name__)

_CONFIRM_LABELS: dict[ConfirmationChoice, str] = {
    ConfirmationChoice.CONFIRM: "CONFIRMER",
    ConfirmationChoice.MODIFY: "MODIFIER",
    ConfirmationChoice.CANCEL: "ANNULER",
}


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    parts = email.header.decode_header(value)
    decoded_parts = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded_parts.append(part)
    return "".join(decoded_parts)


class EmailAdapter(BaseAdapter):
    """Adapter Email — IMAP polling + SMTP envoi."""

    channel = ChannelType.EMAIL

    def __init__(
        self,
        imap_host: str | None = None,
        imap_port: int | None = None,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        address: str | None = None,
        password: str | None = None,
        poll_interval: float = 30.0,
    ) -> None:
        self._imap_host = imap_host or os.environ.get("WORLDAI_EMAIL_IMAP_HOST", "")
        self._imap_port = imap_port or int(os.environ.get("WORLDAI_EMAIL_IMAP_PORT", "993"))
        self._smtp_host = smtp_host or os.environ.get("WORLDAI_EMAIL_SMTP_HOST", "")
        self._smtp_port = smtp_port or int(os.environ.get("WORLDAI_EMAIL_SMTP_PORT", "587"))
        self._address = address or os.environ.get("WORLDAI_EMAIL_ADDRESS", "")
        self._password = password or os.environ.get("WORLDAI_EMAIL_PASSWORD", "")
        self._poll_interval = poll_interval
        self._polling_task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------
    # BaseAdapter — receive
    # ------------------------------------------------------------------

    async def receive(self, raw: dict[str, Any]) -> UnifiedMessage:
        """Parse un dict email normalisé en UnifiedMessage.

        Format attendu pour ``raw`` :
        {
            "from": "sender@example.com",
            "subject": "...",
            "body": "...",
            "message_id": "<id@mail>",
            "in_reply_to": "<parent@mail>" | None,
            "attachments": [{"filename": "...", "content_type": "..."}]  # optionnel
        }
        Ce format est produit par ``_fetch_unseen_emails()`` ou peut être
        envoyé directement via le endpoint POST /webhook/email du gateway.
        """
        sender = raw.get("from", "")
        subject = raw.get("subject", "")
        body = raw.get("body", "")
        message_id = raw.get("message_id", "")
        in_reply_to = raw.get("in_reply_to")

        if not sender:
            raise AdapterError("Email payload missing 'from' field")

        user_id = email.utils.parseaddr(sender)[1] or sender
        session_id = message_id or user_id

        attachments: list[Attachment] = []
        for att in raw.get("attachments", []):
            content_type = att.get("content_type", "application/octet-stream")
            if content_type.startswith("image/"):
                att_type = AttachmentType.IMAGE
            elif content_type.startswith("audio/"):
                att_type = AttachmentType.AUDIO
            else:
                att_type = AttachmentType.DOCUMENT
            attachments.append(
                Attachment(
                    attachment_type=att_type,
                    filename=att.get("filename"),
                    mime_type=content_type,
                    size_bytes=att.get("size_bytes"),
                )
            )

        content = f"Sujet: {subject}\n\n{body}".strip() if subject else body

        return UnifiedMessage(
            channel=ChannelType.EMAIL,
            user_id=user_id,
            session_id=session_id,
            content=content,
            attachments=attachments,
            reply_to=in_reply_to,
            raw_payload=raw,
            metadata={"subject": subject, "from_address": sender, "message_id": message_id},
        )

    # ------------------------------------------------------------------
    # BaseAdapter — send
    # ------------------------------------------------------------------

    async def send(self, original: UnifiedMessage, response_text: str) -> None:
        """Envoie un email de réponse via SMTP."""
        if not self._smtp_host:
            raise AdapterError("WORLDAI_EMAIL_SMTP_HOST is not set")
        if not self._address or not self._password:
            raise AdapterError("WORLDAI_EMAIL_ADDRESS or EMAIL_PASSWORD is not set")

        to_address = original.metadata.get("from_address") or original.user_id
        subject = "Re: " + original.metadata.get("subject", "(no subject)")
        message_id = original.metadata.get("message_id")

        await asyncio.get_event_loop().run_in_executor(
            None,
            self._send_smtp,
            to_address,
            subject,
            response_text,
            message_id,
        )
        self._log("email_sent", to=to_address)

    # ------------------------------------------------------------------
    # BaseAdapter — send_confirmation
    # ------------------------------------------------------------------

    async def send_confirmation(
        self,
        original: UnifiedMessage,
        prompt: str,
        choices: list[ConfirmationChoice] | None = None,
    ) -> None:
        """Envoie un email avec les choix de confirmation listés."""
        active_choices = choices or self.default_choices()
        choices_text = "\n".join(
            f"- Répondez '{_CONFIRM_LABELS[c]}' pour {c.value}" for c in active_choices
        )
        full_text = f"{prompt}\n\n{choices_text}"
        await self.send(original, full_text)

    # ------------------------------------------------------------------
    # IMAP polling
    # ------------------------------------------------------------------

    async def start_polling(
        self,
        callback: Callable[[UnifiedMessage], Awaitable[None]],
    ) -> None:
        """Lance la boucle de polling IMAP en tâche d'arrière-plan."""
        if self._polling_task and not self._polling_task.done():
            return
        self._polling_task = asyncio.create_task(self._poll_loop(callback))
        logger.info("email_polling_started", interval=self._poll_interval)

    async def stop_polling(self) -> None:
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
        logger.info("email_polling_stopped")

    async def _poll_loop(
        self,
        callback: Callable[[UnifiedMessage], Awaitable[None]],
    ) -> None:
        while True:
            try:
                emails = await asyncio.get_event_loop().run_in_executor(
                    None, self._fetch_unseen_emails
                )
                for raw_email in emails:
                    try:
                        msg = await self.receive(raw_email)
                        await callback(msg)
                    except AdapterError as exc:
                        logger.error("email_parse_error", error=str(exc))
            except Exception as exc:
                logger.error("email_poll_error", error=str(exc))
            await asyncio.sleep(self._poll_interval)

    # ------------------------------------------------------------------
    # SMTP helper (synchronous — run in executor)
    # ------------------------------------------------------------------

    def _send_smtp(
        self,
        to: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
    ) -> None:
        msg = MIMEMultipart("alternative")
        msg["From"] = self._address
        msg["To"] = to
        msg["Subject"] = subject
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = in_reply_to

        html_body = body.replace("\n", "<br>")
        msg.attach(MIMEText(body, "plain", "utf-8"))
        msg.attach(MIMEText(f"<html><body>{html_body}</body></html>", "html", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(self._address, self._password)
            server.sendmail(self._address, to, msg.as_string())

    # ------------------------------------------------------------------
    # IMAP helper (synchronous — run in executor)
    # ------------------------------------------------------------------

    def _fetch_unseen_emails(self) -> list[dict[str, Any]]:
        """Se connecte en IMAP SSL et récupère les emails non-lus."""
        if not self._imap_host or not self._address or not self._password:
            return []

        results: list[dict[str, Any]] = []
        try:
            with imaplib.IMAP4_SSL(self._imap_host, self._imap_port) as mail:
                mail.login(self._address, self._password)
                mail.select("INBOX")
                _, data = mail.search(None, "UNSEEN")
                ids = data[0].split() if data[0] else []

                for uid in ids:
                    _, msg_data = mail.fetch(uid, "(RFC822)")
                    for part in msg_data:
                        if not isinstance(part, tuple):
                            continue
                        raw = email_lib.message_from_bytes(part[1])
                        parsed = self._parse_raw_email(raw)
                        if parsed:
                            results.append(parsed)
        except imaplib.IMAP4.error as exc:
            logger.error("imap_error", error=str(exc))

        return results

    def _parse_raw_email(self, msg: email_lib.message.Message) -> dict[str, Any] | None:
        subject = _decode_header_value(msg.get("Subject"))
        from_addr = _decode_header_value(msg.get("From"))
        message_id = msg.get("Message-ID", "")
        in_reply_to = msg.get("In-Reply-To")

        body = ""
        attachments: list[dict[str, Any]] = []
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disp = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_disp:
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            elif "attachment" in content_disp or part.get_filename():
                attachments.append(
                    {
                        "filename": part.get_filename(),
                        "content_type": content_type,
                    }
                )

        if not from_addr:
            return None

        return {
            "from": from_addr,
            "subject": subject,
            "body": body.strip(),
            "message_id": message_id,
            "in_reply_to": in_reply_to,
            "attachments": attachments,
        }
