"""Tests for UnifiedMessage."""

import pytest
from interfaces.gateway.message import (
    Attachment,
    AttachmentType,
    ChannelType,
    ConfirmationChoice,
    UnifiedMessage,
)


class TestUnifiedMessage:
    def test_text_factory(self):
        msg = UnifiedMessage.text(
            channel=ChannelType.TELEGRAM,
            user_id="u1",
            session_id="s1",
            content="hello",
        )
        assert msg.channel == ChannelType.TELEGRAM
        assert msg.user_id == "u1"
        assert msg.content == "hello"
        assert msg.attachments == []
        assert msg.reply_to is None

    def test_has_attachments_false(self):
        msg = UnifiedMessage.text(ChannelType.DISCORD, "u2", "s2", "hi")
        assert not msg.has_attachments

    def test_has_attachments_true(self):
        att = Attachment(attachment_type=AttachmentType.IMAGE, url="http://img.jpg")
        msg = UnifiedMessage(
            channel=ChannelType.SLACK,
            user_id="u3",
            session_id="s3",
            content="see image",
            attachments=[att],
        )
        assert msg.has_attachments

    def test_is_confirmation_false(self):
        msg = UnifiedMessage.text(ChannelType.EMAIL, "u4", "s4", "text")
        assert not msg.is_confirmation

    def test_is_confirmation_true(self):
        msg = UnifiedMessage(
            channel=ChannelType.TELEGRAM,
            user_id="u5",
            session_id="s5",
            content="confirm",
            confirmation_choice=ConfirmationChoice.CONFIRM,
        )
        assert msg.is_confirmation

    def test_all_channel_types(self):
        channels = [
            ChannelType.TELEGRAM,
            ChannelType.DISCORD,
            ChannelType.SLACK,
            ChannelType.EMAIL,
            ChannelType.WHATSAPP,
            ChannelType.IMESSAGE,
            ChannelType.WEBCHAT,
            ChannelType.VOICE,
            ChannelType.API,
        ]
        for ch in channels:
            msg = UnifiedMessage.text(ch, "u", "s", "test")
            assert msg.channel == ch

    def test_confirmation_choices(self):
        for choice in ConfirmationChoice:
            msg = UnifiedMessage(
                channel=ChannelType.API,
                user_id="u",
                session_id="s",
                content="",
                confirmation_choice=choice,
            )
            assert msg.confirmation_choice == choice

    def test_metadata_default_empty(self):
        msg = UnifiedMessage.text(ChannelType.WEBCHAT, "u", "s", "hello")
        assert msg.metadata == {}

    def test_metadata_stored(self):
        msg = UnifiedMessage.text(
            ChannelType.VOICE, "u", "s", "text", metadata={"lang": "fr"}
        )
        assert msg.metadata["lang"] == "fr"

    def test_raw_payload_stored(self):
        payload = {"update_id": 123, "message": {"text": "hi"}}
        msg = UnifiedMessage(
            channel=ChannelType.TELEGRAM,
            user_id="u",
            session_id="s",
            content="hi",
            raw_payload=payload,
        )
        assert msg.raw_payload == payload

    def test_attachment_fields(self):
        att = Attachment(
            attachment_type=AttachmentType.DOCUMENT,
            filename="report.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
        )
        assert att.attachment_type == AttachmentType.DOCUMENT
        assert att.filename == "report.pdf"
        assert att.size_bytes == 1024

    def test_reply_to_set(self):
        msg = UnifiedMessage(
            channel=ChannelType.DISCORD,
            user_id="u",
            session_id="s",
            content="reply",
            reply_to="msg_original_id",
        )
        assert msg.reply_to == "msg_original_id"
