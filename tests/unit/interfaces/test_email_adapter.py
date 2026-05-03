"""Tests for EmailAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from interfaces.adapters.base_adapter import AdapterError
from interfaces.adapters.email_adapter import EmailAdapter
from interfaces.gateway.message import AttachmentType, ChannelType, ConfirmationChoice


@pytest.fixture
def adapter():
    return EmailAdapter(
        imap_host="imap.example.com",
        imap_port=993,
        smtp_host="smtp.example.com",
        smtp_port=587,
        address="bot@example.com",
        password="secret",
    )


def _raw_email(
    from_addr="sender@example.com",
    subject="Test Subject",
    body="Hello!",
    message_id="<msg1@mail>",
    in_reply_to=None,
    attachments=None,
):
    return {
        "from": from_addr,
        "subject": subject,
        "body": body,
        "message_id": message_id,
        "in_reply_to": in_reply_to,
        "attachments": attachments or [],
    }


# ---------------------------------------------------------------------------
# receive
# ---------------------------------------------------------------------------


class TestReceive:
    async def test_basic_email(self, adapter):
        msg = await adapter.receive(_raw_email())
        assert msg.channel == ChannelType.EMAIL
        assert msg.user_id == "sender@example.com"
        assert "Test Subject" in msg.content
        assert "Hello!" in msg.content

    async def test_message_id_as_session(self, adapter):
        msg = await adapter.receive(_raw_email(message_id="<xyz@mail>"))
        assert msg.session_id == "<xyz@mail>"

    async def test_in_reply_to_as_reply_to(self, adapter):
        msg = await adapter.receive(_raw_email(in_reply_to="<parent@mail>"))
        assert msg.reply_to == "<parent@mail>"

    async def test_metadata_contains_subject(self, adapter):
        msg = await adapter.receive(_raw_email(subject="Hello World"))
        assert msg.metadata["subject"] == "Hello World"

    async def test_missing_from_raises(self, adapter):
        raw = _raw_email(from_addr="")
        with pytest.raises(AdapterError, match="from"):
            await adapter.receive(raw)

    async def test_display_name_in_from(self, adapter):
        msg = await adapter.receive(_raw_email(from_addr="John Doe <john@example.com>"))
        assert msg.user_id == "john@example.com"

    async def test_image_attachment(self, adapter):
        raw = _raw_email(attachments=[{"filename": "photo.jpg", "content_type": "image/jpeg"}])
        msg = await adapter.receive(raw)
        assert msg.has_attachments
        att = msg.attachments[0]
        assert att.attachment_type == AttachmentType.IMAGE
        assert att.filename == "photo.jpg"

    async def test_document_attachment(self, adapter):
        raw = _raw_email(
            attachments=[{"filename": "report.pdf", "content_type": "application/pdf"}]
        )
        msg = await adapter.receive(raw)
        att = msg.attachments[0]
        assert att.attachment_type == AttachmentType.DOCUMENT

    async def test_audio_attachment(self, adapter):
        raw = _raw_email(
            attachments=[{"filename": "voice.mp3", "content_type": "audio/mpeg"}]
        )
        msg = await adapter.receive(raw)
        att = msg.attachments[0]
        assert att.attachment_type == AttachmentType.AUDIO

    async def test_no_subject_body_only(self, adapter):
        raw = _raw_email(subject="", body="Just a body")
        msg = await adapter.receive(raw)
        assert msg.content == "Just a body"


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------


class TestSend:
    async def test_send_calls_smtp(self, adapter):
        original = MagicMock()
        original.metadata = {"from_address": "user@example.com", "subject": "Hey", "message_id": "<m1>"}
        original.user_id = "user@example.com"

        with patch.object(adapter, "_send_smtp") as mock_smtp, \
             patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
            await adapter.send(original, "Hi back!")
            mock_loop.return_value.run_in_executor.assert_called_once()

    async def test_send_without_smtp_host_raises(self):
        adapter = EmailAdapter(smtp_host="", address="a@b.com", password="pwd")
        original = MagicMock()
        original.metadata = {"from_address": "user@example.com", "subject": "Hey", "message_id": ""}
        original.user_id = "user@example.com"
        with pytest.raises(AdapterError, match="SMTP_HOST"):
            await adapter.send(original, "hi")

    async def test_send_without_address_raises(self):
        adapter = EmailAdapter(smtp_host="smtp.example.com", address="", password="")
        original = MagicMock()
        original.metadata = {}
        original.user_id = "u@example.com"
        with pytest.raises(AdapterError, match="ADDRESS"):
            await adapter.send(original, "hi")


# ---------------------------------------------------------------------------
# send_confirmation
# ---------------------------------------------------------------------------


class TestSendConfirmation:
    async def test_sends_all_choices_by_default(self, adapter):
        original = MagicMock()
        original.metadata = {"from_address": "u@e.com", "subject": "Re: Test", "message_id": ""}
        original.user_id = "u@e.com"

        with patch.object(adapter, "send", new_callable=AsyncMock) as mock_send:
            await adapter.send_confirmation(original, "Confirm action?")
            text_sent = mock_send.call_args[0][1]
            assert "CONFIRMER" in text_sent
            assert "MODIFIER" in text_sent
            assert "ANNULER" in text_sent

    async def test_custom_choices(self, adapter):
        original = MagicMock()
        original.metadata = {}
        original.user_id = "u@e.com"

        with patch.object(adapter, "send", new_callable=AsyncMock) as mock_send:
            await adapter.send_confirmation(
                original,
                "Delete?",
                choices=[ConfirmationChoice.CONFIRM, ConfirmationChoice.CANCEL],
            )
            text_sent = mock_send.call_args[0][1]
            assert "CONFIRMER" in text_sent
            assert "ANNULER" in text_sent
            assert "MODIFIER" not in text_sent


# ---------------------------------------------------------------------------
# IMAP polling
# ---------------------------------------------------------------------------


class TestPolling:
    async def test_start_stop_polling(self, adapter):
        callback = AsyncMock()
        with patch.object(adapter, "_fetch_unseen_emails", return_value=[]):
            await adapter.start_polling(callback)
            assert adapter._polling_task is not None
            assert not adapter._polling_task.done()
            await adapter.stop_polling()

    async def test_start_polling_idempotent(self, adapter):
        callback = AsyncMock()
        with patch.object(adapter, "_fetch_unseen_emails", return_value=[]):
            await adapter.start_polling(callback)
            task1 = adapter._polling_task
            await adapter.start_polling(callback)  # second call should be noop
            assert adapter._polling_task is task1
            await adapter.stop_polling()
