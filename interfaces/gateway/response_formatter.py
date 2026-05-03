"""ResponseFormatter — adapte AgentResponse au format natif de chaque canal."""

from __future__ import annotations

from interfaces.gateway.message import ChannelType


class ResponseFormatter:
    """Formate le texte d'une réponse agent selon le canal de destination.

    Chaque canal a ses propres conventions :
    - Telegram : Markdown V2 (échappement requis)
    - Discord   : Markdown classique + embeds possibles
    - Slack     : mrkdwn (subset Markdown propriétaire)
    - Email     : HTML basique + fallback texte brut
    - WhatsApp  : texte brut, *gras*, _italique_
    - iMessage  : texte brut simple
    - WebChat   : Markdown (rendu côté client)
    - Voice     : texte brut (TTS ne comprend pas le Markdown)
    - API       : texte brut, aucune transformation
    """

    # Caractères à échapper pour Telegram MarkdownV2
    _TG_ESCAPE = r"\_*[]()~`>#+-=|{}.!"

    def format(self, text: str, channel: ChannelType) -> str:
        dispatch = {
            ChannelType.TELEGRAM: self._telegram,
            ChannelType.DISCORD: self._discord,
            ChannelType.SLACK: self._slack,
            ChannelType.EMAIL: self._email,
            ChannelType.WHATSAPP: self._whatsapp,
            ChannelType.IMESSAGE: self._plain,
            ChannelType.WEBCHAT: self._webchat,
            ChannelType.VOICE: self._voice,
            ChannelType.API: self._plain,
        }
        formatter = dispatch.get(channel, self._plain)
        return formatter(text)

    # ------------------------------------------------------------------
    # Per-channel formatters
    # ------------------------------------------------------------------

    def _telegram(self, text: str) -> str:
        """Échappe les caractères spéciaux Telegram MarkdownV2."""
        result = []
        in_code = False
        for char in text:
            if char == "`":
                in_code = not in_code
                result.append(char)
            elif in_code:
                result.append(char)
            elif char in self._TG_ESCAPE:
                result.append(f"\\{char}")
            else:
                result.append(char)
        return "".join(result)

    def _discord(self, text: str) -> str:
        # Discord accepte le Markdown standard tel quel
        return text

    def _slack(self, text: str) -> str:
        # mrkdwn : ** → * pour gras, __ → _ pour italique
        return text.replace("**", "*").replace("__", "_")

    def _email(self, text: str) -> str:
        # Wrap in minimal HTML paragraph blocks
        lines = text.splitlines()
        html_lines = [f"<p>{line}</p>" if line.strip() else "" for line in lines]
        return "\n".join(html_lines)

    def _whatsapp(self, text: str) -> str:
        # WhatsApp comprend *gras* et _italique_ nativement
        return text.replace("**", "*").replace("__", "_")

    def _webchat(self, text: str) -> str:
        return text  # Markdown rendu côté client

    def _voice(self, text: str) -> str:
        """Supprime tout Markdown — le TTS lit du texte brut."""
        import re

        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)   # **bold**
        text = re.sub(r"\*(.+?)\*", r"\1", text)         # *italic*
        text = re.sub(r"__(.+?)__", r"\1", text)          # __bold__
        text = re.sub(r"_(.+?)_", r"\1", text)             # _italic_
        text = re.sub(r"`{1,3}.+?`{1,3}", "", text)        # code
        text = re.sub(r"#{1,6}\s*", "", text)              # headers
        return text.strip()

    def _plain(self, text: str) -> str:
        return text
