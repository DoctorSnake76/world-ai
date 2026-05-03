"""BaseAdapter — interface abstraite que chaque canal doit implémenter."""

from __future__ import annotations

import abc
from typing import Any

import structlog

from interfaces.gateway.message import ChannelType, ConfirmationChoice, UnifiedMessage

logger = structlog.get_logger(__name__)


class AdapterError(Exception):
    """Raised when an adapter fails to send or parse a message."""


class BaseAdapter(abc.ABC):
    """Contrat minimal que tout adapter de canal doit respecter.

    Cycle de vie :
    1. ``receive(raw)`` — parse le payload brut → UnifiedMessage
    2. ``send(msg, response)`` — envoie la réponse formatée sur le canal
    3. ``send_confirmation(msg, prompt, choices)`` — envoie un gate Oui/Non/Modifier
    """

    channel: ChannelType  # doit être défini dans chaque sous-classe

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not isinstance(getattr(cls, "channel", None), ChannelType):
            raise TypeError(
                f"{cls.__name__} must define a class-level 'channel: ChannelType'"
            )

    # ------------------------------------------------------------------
    # Abstract API
    # ------------------------------------------------------------------

    @abc.abstractmethod
    async def receive(self, raw: dict[str, Any]) -> UnifiedMessage:
        """Parse le payload brut du canal et retourne un UnifiedMessage normalisé."""

    @abc.abstractmethod
    async def send(self, original: UnifiedMessage, response_text: str) -> None:
        """Envoie ``response_text`` sur le canal d'où provient ``original``."""

    @abc.abstractmethod
    async def send_confirmation(
        self,
        original: UnifiedMessage,
        prompt: str,
        choices: list[ConfirmationChoice] | None = None,
    ) -> None:
        """Envoie un gate de confirmation adaptatif au format natif du canal.

        Si ``choices`` est None, envoie les trois choix par défaut :
        CONFIRM / MODIFY / CANCEL.
        """

    # ------------------------------------------------------------------
    # Helpers partagés
    # ------------------------------------------------------------------

    def default_choices(self) -> list[ConfirmationChoice]:
        return list(ConfirmationChoice)

    def _log(self, event: str, **kw: Any) -> None:
        logger.info(event, channel=self.channel.value, **kw)

    def _log_error(self, event: str, **kw: Any) -> None:
        logger.error(event, channel=self.channel.value, **kw)
