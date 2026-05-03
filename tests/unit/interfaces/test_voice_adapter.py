"""Tests for VoiceAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from interfaces.adapters.base_adapter import AdapterError
from interfaces.adapters.voice_adapter import VoiceAdapter
from interfaces.gateway.message import ChannelType, ConfirmationChoice


@pytest.fixture
def adapter():
    return VoiceAdapter(whisper_model="base", tts_backend="none")


# ---------------------------------------------------------------------------
# receive — pre-transcribed content
# ---------------------------------------------------------------------------


class TestReceivePreTranscribed:
    async def test_text_content_passthrough(self, adapter):
        raw = {"user_id": "u1", "session_id": "s1", "content": "bonjour"}
        msg = await adapter.receive(raw)
        assert msg.channel == ChannelType.VOICE
        assert msg.user_id == "u1"
        assert msg.content == "bonjour"

    async def test_missing_user_id_raises(self, adapter):
        with pytest.raises(AdapterError, match="user_id"):
            await adapter.receive({"content": "hello"})

    async def test_session_id_defaults_to_user_id(self, adapter):
        raw = {"user_id": "u2", "content": "hi"}
        msg = await adapter.receive(raw)
        assert msg.session_id == "u2"

    async def test_missing_audio_and_content_raises(self, adapter):
        with pytest.raises(AdapterError, match="audio_path"):
            await adapter.receive({"user_id": "u1", "session_id": "s1"})


# ---------------------------------------------------------------------------
# receive — confirmation detection
# ---------------------------------------------------------------------------


class TestConfirmationDetection:
    async def test_oui_maps_to_confirm(self, adapter):
        msg = await adapter.receive({"user_id": "u", "content": "oui"})
        assert msg.confirmation_choice == ConfirmationChoice.CONFIRM

    async def test_non_maps_to_cancel(self, adapter):
        msg = await adapter.receive({"user_id": "u", "content": "non"})
        assert msg.confirmation_choice == ConfirmationChoice.CANCEL

    async def test_confirmer_maps_to_confirm(self, adapter):
        msg = await adapter.receive({"user_id": "u", "content": "confirmer"})
        assert msg.confirmation_choice == ConfirmationChoice.CONFIRM

    async def test_modifier_maps_to_modify(self, adapter):
        msg = await adapter.receive({"user_id": "u", "content": "modifier"})
        assert msg.confirmation_choice == ConfirmationChoice.MODIFY

    async def test_annuler_maps_to_cancel(self, adapter):
        msg = await adapter.receive({"user_id": "u", "content": "annuler."})
        assert msg.confirmation_choice == ConfirmationChoice.CANCEL

    async def test_regular_text_no_choice(self, adapter):
        msg = await adapter.receive({"user_id": "u", "content": "quel temps fait-il ?"})
        assert msg.confirmation_choice is None

    async def test_yes_maps_to_confirm(self, adapter):
        msg = await adapter.receive({"user_id": "u", "content": "yes"})
        assert msg.confirmation_choice == ConfirmationChoice.CONFIRM


# ---------------------------------------------------------------------------
# receive — Whisper transcription (mocked)
# ---------------------------------------------------------------------------


class TestReceiveWithWhisper:
    async def test_transcription_via_audio_path(self, adapter):
        with patch.object(adapter, "_transcribe", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = "transcribed text"
            raw = {"user_id": "u1", "session_id": "s1", "audio_path": "/tmp/voice.ogg"}
            msg = await adapter.receive(raw)
            assert msg.content == "transcribed text"
            assert msg.has_attachments

    async def test_transcription_via_audio_data(self, adapter):
        with patch.object(adapter, "_transcribe", new_callable=AsyncMock) as mock_t:
            mock_t.return_value = "from bytes"
            raw = {
                "user_id": "u1",
                "session_id": "s1",
                "audio_data": b"fake-audio",
                "audio_format": "mp3",
            }
            msg = await adapter.receive(raw)
            assert msg.content == "from bytes"


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------


class TestSend:
    async def test_send_calls_speak(self, adapter):
        original = MagicMock()
        original.user_id = "u1"

        with patch.object(adapter, "_speak") as mock_speak, \
             patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
            await adapter.send(original, "Hello!")
            mock_loop.return_value.run_in_executor.assert_called_once()

    def test_speak_none_backend_logs(self, adapter):
        # Should not raise, just log
        adapter._speak("Test text")

    def test_speak_pyttsx3_not_installed_no_raise(self, adapter):
        adapter._tts_backend = "pyttsx3"
        with patch.dict("sys.modules", {"pyttsx3": None}):
            # ImportError caught internally
            adapter._speak_pyttsx3("test")


# ---------------------------------------------------------------------------
# send_confirmation
# ---------------------------------------------------------------------------


class TestSendConfirmation:
    async def test_reads_options_aloud(self, adapter):
        original = MagicMock()
        original.user_id = "u1"

        with patch.object(adapter, "send", new_callable=AsyncMock) as mock_send:
            await adapter.send_confirmation(original, "Confirm action?")
            text = mock_send.call_args[0][1]
            assert "Confirm action?" in text
            assert "Confirmer" in text
            assert "Annuler" in text

    async def test_custom_choices(self, adapter):
        original = MagicMock()

        with patch.object(adapter, "send", new_callable=AsyncMock) as mock_send:
            await adapter.send_confirmation(
                original,
                "Delete?",
                choices=[ConfirmationChoice.CONFIRM, ConfirmationChoice.CANCEL],
            )
            text = mock_send.call_args[0][1]
            assert "Confirmer" in text
            assert "Annuler" in text
            assert "Modifier" not in text


# ---------------------------------------------------------------------------
# _transcribe_sync — Whisper not installed
# ---------------------------------------------------------------------------


class TestTranscribeSync:
    def test_whisper_not_installed_returns_stub(self, adapter):
        with patch.dict("sys.modules", {"whisper": None}):
            result = adapter._transcribe_sync("/tmp/audio.ogg", None, "ogg")
            assert "indisponible" in result
