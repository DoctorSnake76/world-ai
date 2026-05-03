"""UnifiedMessage — format normalisé commun à tous les canaux entrants."""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ChannelType(str, Enum):
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SLACK = "slack"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    IMESSAGE = "imessage"
    WEBCHAT = "webchat"
    VOICE = "voice"
    API = "api"


class AttachmentType(str, Enum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    OTHER = "other"


class Attachment(BaseModel):
    attachment_type: AttachmentType
    url: str | None = None
    data: bytes | None = None
    filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None

    model_config = {"arbitrary_types_allowed": True}


class ConfirmationChoice(str, Enum):
    """Réponse possible à un gate de confirmation."""

    CONFIRM = "confirm"
    MODIFY = "modify"
    CANCEL = "cancel"


class UnifiedMessage(BaseModel):
    """Message normalisé — l'agent ne connaît pas le canal d'origine."""

    channel: ChannelType
    user_id: str
    session_id: str
    content: str
    attachments: list[Attachment] = Field(default_factory=list)
    reply_to: str | None = None
    confirmation_choice: ConfirmationChoice | None = None
    raw_payload: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def has_attachments(self) -> bool:
        return len(self.attachments) > 0

    @property
    def is_confirmation(self) -> bool:
        return self.confirmation_choice is not None

    @classmethod
    def text(
        cls,
        channel: ChannelType,
        user_id: str,
        session_id: str,
        content: str,
        **kwargs: Any,
    ) -> "UnifiedMessage":
        """Constructeur rapide pour message texte simple."""
        return cls(
            channel=channel,
            user_id=user_id,
            session_id=session_id,
            content=content,
            **kwargs,
        )
