"""Tests for TelegramAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from interfaces.adapters.base_adapter import AdapterError
from interfaces.adapters.telegram_adapter import TelegramAdapter
from interfaces.gateway.message import (
    AttachmentType,
    ChannelType,
    ConfirmationChoice,
)


@pytest.fixture
def adapter():
    return TelegramAdapter(token="test-token-123")


# ---------------------------------------------------------------------------
# receive — text message
# ---------------------------------------------------------------------------


class TestReceiveText:
    async def test_simple_text(self, adapter):
        raw = {
            "update_id": 1,
            "message": {
                "chat": {"id": 100},
                "from": {"id": 42},
                "text": "hello world",
            },
        }
        msg = await adapter.receive(raw)
        assert msg.channel == ChannelType.TELEGRAM
        assert msg.user_id == "42"
        assert msg.session_id == "100"
        assert msg.content == "hello world"
        assert not msg.has_attachments

    async def test_edited_message(self, adapter):
        raw = {
            "edited_message": {
                "chat": {"id": 55},
                "from": {"id": 7},
                "text": "edited",
            }
        }
        msg = await adapter.receive(raw)
        assert msg.content == "edited"

    async def test_empty_text(self, adapter):
        raw = {"message": {"chat": {"id": 1}, "from": {"id": 2}}}
        msg = await adapter.receive(raw)
        assert msg.content == ""

    async def test_no_message_raises(self, adapter):
        with pytest.raises(AdapterError, match="Unsupported"):
            await adapter.receive({"update_id": 99})


# ---------------------------------------------------------------------------
# receive — attachments
# ---------------------------------------------------------------------------


class TestReceiveAttachments:
    async def test_voice_attachment(self, adapter):
        raw = {
            "message": {
                "chat": {"id": 1},
                "from": {"id": 2},
                "voice": {"file_id": "fv1", "file_size": 500, "mime_type": "audio/ogg"},
            }
        }
        msg = await adapter.receive(raw)
        assert msg.has_attachments
        att = msg.attachments[0]
        assert att.attachment_type == AttachmentType.AUDIO
        assert att.metadata["file_id"] == "fv1"

    async def test_photo_takes_largest(self, adapter):
        raw = {
            "message": {
                "chat": {"id": 1},
                "from": {"id": 2},
                "photo": [
                    {"file_id": "small", "file_size": 100},
                    {"file_id": "large", "file_size": 9000},
                ],
            }
        }
        msg = await adapter.receive(raw)
        assert msg.attachments[0].metadata["file_id"] == "large"

    async def test_document_attachment(self, adapter):
        raw = {
            "message": {
                "chat": {"id": 1},
                "from": {"id": 2},
                "document": {
                    "file_id": "doc1",
                    "file_name": "report.pdf",
                    "mime_type": "application/pdf",
                },
            }
        }
        msg = await adapter.receive(raw)
        att = msg.attachments[0]
        assert att.attachment_type == AttachmentType.DOCUMENT
        assert att.filename == "report.pdf"

    async def test_caption_used_as_text(self, adapter):
        raw = {
            "message": {
                "chat": {"id": 1},
                "from": {"id": 2},
                "caption": "see this photo",
                "photo": [{"file_id": "p1", "file_size": 100}],
            }
        }
        msg = await adapter.receive(raw)
        assert msg.content == "see this photo"


# ---------------------------------------------------------------------------
# receive — callback_query (confirmation)
# ---------------------------------------------------------------------------


class TestReceiveCallbackQuery:
    async def test_confirm_callback(self, adapter):
        raw = {
            "callback_query": {
                "from": {"id": 9},
                "data": "confirm",
                "message": {"chat": {"id": 100}},
            }
        }
        msg = await adapter.receive(raw)
        assert msg.is_confirmation
        assert msg.confirmation_choice == ConfirmationChoice.CONFIRM

    async def test_cancel_callback(self, adapter):
        raw = {
            "callback_query": {
                "from": {"id": 9},
                "data": "cancel",
                "message": {"chat": {"id": 100}},
            }
        }
        msg = await adapter.receive(raw)
        assert msg.confirmation_choice == ConfirmationChoice.CANCEL

    async def test_unknown_callback_data(self, adapter):
        raw = {
            "callback_query": {
                "from": {"id": 9},
                "data": "unknown_action",
                "message": {"chat": {"id": 100}},
            }
        }
        msg = await adapter.receive(raw)
        assert msg.confirmation_choice is None


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------


class TestSend:
    async def test_send_calls_api(self, adapter):
        original = MagicMock()
        original.session_id = "100"

        with patch.object(adapter, "_call_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {"ok": True}
            await adapter.send(original, "Hello world")
            mock_api.assert_called_once()
            call_args = mock_api.call_args
            assert call_args[0][0] == "sendMessage"
            assert call_args[0][1]["chat_id"] == "100"
            assert call_args[0][1]["parse_mode"] == "MarkdownV2"

    async def test_send_without_token_raises(self):
        adapter = TelegramAdapter(token="")
        original = MagicMock()
        original.session_id = "100"
        with pytest.raises(AdapterError, match="TOKEN"):
            await adapter.send(original, "hi")


# ---------------------------------------------------------------------------
# send_confirmation
# ---------------------------------------------------------------------------


class TestSendConfirmation:
    async def test_sends_inline_keyboard(self, adapter):
        original = MagicMock()
        original.session_id = "200"

        with patch.object(adapter, "_call_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {"ok": True}
            await adapter.send_confirmation(original, "Confirm action?")
            payload = mock_api.call_args[0][1]
            assert "reply_markup" in payload
            keyboard = payload["reply_markup"]["inline_keyboard"]
            assert len(keyboard) == 3  # default: all 3 choices

    async def test_custom_choices(self, adapter):
        original = MagicMock()
        original.session_id = "200"

        with patch.object(adapter, "_call_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {"ok": True}
            await adapter.send_confirmation(
                original,
                "Delete?",
                choices=[ConfirmationChoice.CONFIRM, ConfirmationChoice.CANCEL],
            )
            keyboard = mock_api.call_args[0][1]["reply_markup"]["inline_keyboard"]
            assert len(keyboard) == 2


# ---------------------------------------------------------------------------
# _call_api error handling
# ---------------------------------------------------------------------------


class TestCallApiErrors:
    async def test_http_status_error_raises_adapter_error(self, adapter):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        exc = httpx.HTTPStatusError("403", request=MagicMock(), response=mock_response)

        with patch.object(adapter, "_get_client", new_callable=AsyncMock) as mock_client:
            client_instance = AsyncMock()
            client_instance.post.side_effect = exc
            mock_client.return_value = client_instance

            with pytest.raises(AdapterError, match="403"):
                await adapter._call_api("sendMessage", {})

    async def test_request_error_raises_adapter_error(self, adapter):
        exc = httpx.RequestError("connection refused", request=MagicMock())

        with patch.object(adapter, "_get_client", new_callable=AsyncMock) as mock_client:
            client_instance = AsyncMock()
            client_instance.post.side_effect = exc
            mock_client.return_value = client_instance

            with pytest.raises(AdapterError, match="request failed"):
                await adapter._call_api("sendMessage", {})
