"""VoiceAdapter — canal Voix (Whisper STT input + TTS pyttsx3/Coqui output).

Transport entrant : UnifiedMessage avec attachment audio → transcription Whisper
Envoi            : texte → TTS (pyttsx3 ou Coqui) → audio (ou texte si TTS absent)

Whisper et pyttsx3 sont des dépendances optionnelles.
Si elles ne sont pas installées, l'adapter fonctionne en mode stub :
- STT : retourne un message d'erreur explicite
- TTS : log le texte sans le synthétiser

Environnement :
  WORLDAI_WHISPER_MODEL=medium   # tiny | base | small | medium | large
  WORLDAI_TTS_BACKEND=pyttsx3   # pyttsx3 | coqui | none
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

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

_WHISPER_MODEL_NAME = os.environ.get("WORLDAI_WHISPER_MODEL", "base")
_TTS_BACKEND = os.environ.get("WORLDAI_TTS_BACKEND", "none")

_CONFIRM_LABELS: dict[ConfirmationChoice, str] = {
    ConfirmationChoice.CONFIRM: "Confirmer",
    ConfirmationChoice.MODIFY: "Modifier",
    ConfirmationChoice.CANCEL: "Annuler",
}

_VOICE_KEYWORDS_TO_CHOICE: dict[str, ConfirmationChoice] = {
    "confirmer": ConfirmationChoice.CONFIRM,
    "confirm": ConfirmationChoice.CONFIRM,
    "oui": ConfirmationChoice.CONFIRM,
    "yes": ConfirmationChoice.CONFIRM,
    "modifier": ConfirmationChoice.MODIFY,
    "modify": ConfirmationChoice.MODIFY,
    "annuler": ConfirmationChoice.CANCEL,
    "cancel": ConfirmationChoice.CANCEL,
    "non": ConfirmationChoice.CANCEL,
    "no": ConfirmationChoice.CANCEL,
}


def _detect_voice_confirmation(text: str) -> ConfirmationChoice | None:
    normalized = text.strip().lower().rstrip(".")
    return _VOICE_KEYWORDS_TO_CHOICE.get(normalized)


class VoiceAdapter(BaseAdapter):
    """Adapter Voix — Whisper STT + TTS local."""

    channel = ChannelType.VOICE

    def __init__(
        self,
        whisper_model: str | None = None,
        tts_backend: str | None = None,
    ) -> None:
        self._whisper_model_name = whisper_model or _WHISPER_MODEL_NAME
        self._tts_backend = tts_backend or _TTS_BACKEND
        self._whisper_model: Any = None  # lazy-loaded
        self._tts_engine: Any = None  # lazy-loaded

    # ------------------------------------------------------------------
    # BaseAdapter — receive
    # ------------------------------------------------------------------

    async def receive(self, raw: dict[str, Any]) -> UnifiedMessage:
        """Parse un payload voix en UnifiedMessage.

        Format attendu :
        {
            "user_id": "...",
            "session_id": "...",
            "audio_path": "/tmp/voice.ogg"   # chemin vers fichier audio local
            # OU
            "audio_data": b"..."              # bytes audio bruts
            "audio_format": "ogg"             # format si audio_data fourni
            # OU
            "content": "..."                  # texte déjà transcrit (pour tests)
        }
        """
        user_id = raw.get("user_id", "")
        if not user_id:
            raise AdapterError("Voice payload missing 'user_id'")

        session_id = raw.get("session_id", user_id)

        # Si le texte est déjà transcrit (mode test ou via voice_handler)
        if "content" in raw and raw["content"]:
            text = raw["content"]
            choice = _detect_voice_confirmation(text)
            return UnifiedMessage(
                channel=ChannelType.VOICE,
                user_id=user_id,
                session_id=session_id,
                content=text,
                confirmation_choice=choice,
                raw_payload=raw,
            )

        # Transcription depuis fichier audio
        audio_path = raw.get("audio_path")
        audio_data = raw.get("audio_data")
        audio_format = raw.get("audio_format", "ogg")

        if not audio_path and not audio_data:
            raise AdapterError("Voice payload must include 'audio_path', 'audio_data', or 'content'")

        text = await self._transcribe(audio_path, audio_data, audio_format)
        choice = _detect_voice_confirmation(text)

        attachment: Attachment | None = None
        if audio_path:
            attachment = Attachment(
                attachment_type=AttachmentType.AUDIO,
                url=audio_path,
                mime_type=f"audio/{audio_format}",
            )

        return UnifiedMessage(
            channel=ChannelType.VOICE,
            user_id=user_id,
            session_id=session_id,
            content=text,
            attachments=[attachment] if attachment else [],
            confirmation_choice=choice,
            raw_payload=raw,
        )

    # ------------------------------------------------------------------
    # BaseAdapter — send
    # ------------------------------------------------------------------

    async def send(self, original: UnifiedMessage, response_text: str) -> None:
        """Synthétise le texte en audio (TTS) et le joue ou l'enregistre."""
        await asyncio.get_event_loop().run_in_executor(
            None, self._speak, response_text
        )
        self._log("voice_sent", user_id=original.user_id)

    # ------------------------------------------------------------------
    # BaseAdapter — send_confirmation
    # ------------------------------------------------------------------

    async def send_confirmation(
        self,
        original: UnifiedMessage,
        prompt: str,
        choices: list[ConfirmationChoice] | None = None,
    ) -> None:
        """Lit les choix de confirmation à voix haute."""
        active_choices = choices or self.default_choices()
        options = ", ".join(_CONFIRM_LABELS[c] for c in active_choices)
        full_text = f"{prompt}. Options : {options}."
        await self.send(original, full_text)

    # ------------------------------------------------------------------
    # Whisper STT (async, run in executor)
    # ------------------------------------------------------------------

    async def _transcribe(
        self,
        audio_path: str | None,
        audio_data: bytes | None,
        audio_format: str,
    ) -> str:
        return await asyncio.get_event_loop().run_in_executor(
            None, self._transcribe_sync, audio_path, audio_data, audio_format
        )

    def _transcribe_sync(
        self,
        audio_path: str | None,
        audio_data: bytes | None,
        audio_format: str,
    ) -> str:
        try:
            import whisper
        except ImportError:
            logger.warning("whisper_not_installed")
            return "[Transcription indisponible : whisper non installé]"

        model = self._get_whisper_model()
        tmp_path: str | None = None

        try:
            if audio_data and not audio_path:
                suffix = f".{audio_format}"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(audio_data)
                    tmp_path = tmp.name
                audio_path = tmp_path

            result = model.transcribe(audio_path)
            return result.get("text", "").strip()
        except Exception as exc:
            logger.error("whisper_transcribe_error", error=str(exc))
            raise AdapterError(f"Transcription failed: {exc}") from exc
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    def _get_whisper_model(self) -> Any:
        if self._whisper_model is None:
            import whisper
            logger.info("whisper_model_loading", model=self._whisper_model_name)
            self._whisper_model = whisper.load_model(self._whisper_model_name)
        return self._whisper_model

    # ------------------------------------------------------------------
    # TTS (synchronous, run in executor)
    # ------------------------------------------------------------------

    def _speak(self, text: str) -> None:
        if self._tts_backend == "pyttsx3":
            self._speak_pyttsx3(text)
        elif self._tts_backend == "coqui":
            self._speak_coqui(text)
        else:
            logger.info("voice_tts_stub", text=text[:100])

    def _speak_pyttsx3(self, text: str) -> None:
        try:
            import pyttsx3
        except ImportError:
            logger.warning("pyttsx3_not_installed")
            return

        if self._tts_engine is None:
            self._tts_engine = pyttsx3.init()
        engine = self._tts_engine
        engine.say(text)
        engine.runAndWait()

    def _speak_coqui(self, text: str) -> None:
        # Coqui TTS stub — Phase 2 implementation
        logger.info("coqui_tts_stub", text=text[:100])
