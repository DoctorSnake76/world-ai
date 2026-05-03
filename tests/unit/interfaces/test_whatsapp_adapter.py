"""Tests for WhatsAppAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from interfaces.adapters.base_adapter import AdapterError
from interfaces.adapters.whatsapp_adapter import WhatsAppAdapter
from interfaces.gateway.message import AttachmentType, ChannelType, ConfirmationChoice


@pytest.fixture
def adapter():
    return WhatsAppAdapter(
        account_sid="ACtest123",
        auth_token="authtoken123",
        whatsapp_number="+14155238886",
    )


def _twilio_payload(body="Hello", from_num="whatsapp:+33612345678", wa_id="33612345678", num_media=0, **extra):
    data = {
        "Body": body,
        "From": from_num,
        "To": "whatsapp:+14155238886",
        "WaId": wa_id,
        "NumMedia": str(num_media),
    }
    data.update(extra)
    return data


# ---------------------------------------------------------------------------
# receive
# ---------------------------------------------------------------------------


class TestReceive:
    async def test_basic_message(self, adapter):
        msg = await adapter.receive(_twilio_payload())
        assert msg.channel == ChannelType.WHATSAPP
        assert msg.user_id == "33612345678"
        assert msg.session_id == "33612345678"
        assert msg.content == "Hello"

    async def test_missing_from_raises(self, adapter):
        with pytest.raises(AdapterError, match="From"):
            await adapter.receive({"Body": "hi"})

    async def test_wa_id_preferred_over_from(self, adapter):
        msg = await adapter.receive(_twilio_payload(wa_id="123456", from_num="whatsapp:+1999"))
        assert msg.user_id == "123456"

    async def test_from_without_wa_id(self, adapter):
        msg = await adapter.receive(_twilio_payload(wa_id="", from_num="whatsapp:+33699"))
        assert msg.user_id == "+33699"

    async def test_confirmation_by_text(self, adapter):
        msg = await adapter.receive(_twilio_payload(body="oui"))
        assert msg.is_confirmation
        assert msg.confirmation_choice == ConfirmationChoice.CONFIRM

    async def test_cancel_by_number(self, adapter):
        msg = await adapter.receive(_twilio_payload(body="3"))
        assert msg.confirmation_choice == ConfirmationChoice.CANCEL

    async def test_regular_text_no_confirmation(self, adapter):
        msg = await adapter.receive(_twilio_payload(body="What's the weather?"))
        assert msg.confirmation_choice is None

    async def test_image_attachment(self, adapter):
        raw = _twilio_payload(
            num_media=1,
            MediaUrl0="https://example.com/img.jpg",
            MediaContentType0="image/jpeg",
        )
        msg = await adapter.receive(raw)
        assert msg.has_attachments
        att = msg.attachments[0]
        assert att.attachment_type == AttachmentType.IMAGE
        assert att.url == "https://example.com/img.jpg"

    async def test_audio_attachment(self, adapter):
        raw = _twilio_payload(
            num_media=1,
            MediaUrl0="https://example.com/voice.ogg",
            MediaContentType0="audio/ogg",
        )
        msg = await adapter.receive(raw)
        assert msg.attachments[0].attachment_type == AttachmentType.AUDIO

    async def test_document_attachment(self, adapter):
        raw = _twilio_payload(
            num_media=1,
            MediaUrl0="https://example.com/file.pdf",
            MediaContentType0="application/pdf",
        )
        msg = await adapter.receive(raw)
        assert msg.attachments[0].attachment_type == AttachmentType.DOCUMENT

    async def test_multiple_attachments(self, adapter):
        raw = _twilio_payload(
            num_media=2,
            MediaUrl0="https://example.com/a.jpg",
            MediaContentType0="image/jpeg",
            MediaUrl1="https://example.com/b.mp3",
            MediaContentType1="audio/mpeg",
        )
        msg = await adapter.receive(raw)
        assert len(msg.attachments) == 2


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------


class TestSend:
    async def test_send_calls_twilio_api(self, adapter):
        original = MagicMock()
        original.metadata = {"from_number": "whatsapp:+33612345678"}
        original.user_id = "33612345678"

        with patch.object(adapter, "_call_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {"sid": "SM123"}
            await adapter.send(original, "Hello back!")
            form = mock_api.call_args[0][0]
            assert form["To"] == "whatsapp:+33612345678"
            assert form["Body"] == "Hello back!"

    async def test_send_prepends_whatsapp_prefix(self, adapter):
        original = MagicMock()
        original.metadata = {"from_number": "whatsapp:+33699"}
        original.user_id = "33699"

        with patch.object(adapter, "_call_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {}
            await adapter.send(original, "hi")
            form = mock_api.call_args[0][0]
            assert form["From"].startswith("whatsapp:")

    async def test_send_without_credentials_raises(self):
        adapter = WhatsAppAdapter(account_sid="", auth_token="", whatsapp_number="")
        original = MagicMock()
        original.metadata = {}
        original.user_id = "123"
        with pytest.raises(AdapterError, match="ACCOUNT_SID"):
            await adapter.send(original, "hi")

    async def test_send_without_number_raises(self):
        adapter = WhatsAppAdapter(account_sid="AC1", auth_token="tok", whatsapp_number="")
        original = MagicMock()
        original.metadata = {"from_number": "whatsapp:+1"}
        original.user_id = "1"
        with pytest.raises(AdapterError, match="NUMBER"):
            await adapter.send(original, "hi")


# ---------------------------------------------------------------------------
# send_confirmation
# ---------------------------------------------------------------------------


class TestSendConfirmation:
    async def test_sends_numbered_options(self, adapter):
        original = MagicMock()
        original.metadata = {"from_number": "whatsapp:+1"}
        original.user_id = "1"

        with patch.object(adapter, "send", new_callable=AsyncMock) as mock_send:
            await adapter.send_confirmation(original, "Confirm deletion?")
            text = mock_send.call_args[0][1]
            assert "1 - Confirmer" in text
            assert "2 - Modifier" in text
            assert "3 - Annuler" in text

    async def test_custom_choices(self, adapter):
        original = MagicMock()
        with patch.object(adapter, "send", new_callable=AsyncMock) as mock_send:
            await adapter.send_confirmation(
                original,
                "Confirm?",
                choices=[ConfirmationChoice.CONFIRM, ConfirmationChoice.CANCEL],
            )
            text = mock_send.call_args[0][1]
            assert "1 - Confirmer" in text
            assert "3 - Annuler" in text
            assert "2 - Modifier" not in text


# ---------------------------------------------------------------------------
# _call_api errors
# ---------------------------------------------------------------------------


class TestCallApiErrors:
    async def test_http_error_raises(self, adapter):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        exc = httpx.HTTPStatusError("401", request=MagicMock(), response=mock_resp)

        with patch.object(adapter, "_get_client", new_callable=AsyncMock) as mock_client:
            client = AsyncMock()
            client.post.side_effect = exc
            mock_client.return_value = client

            with pytest.raises(AdapterError, match="401"):
                await adapter._call_api({"To": "w:+1", "From": "w:+2", "Body": "hi"})
