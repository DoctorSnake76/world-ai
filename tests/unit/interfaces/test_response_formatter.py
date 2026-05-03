"""Tests for ResponseFormatter."""

import pytest
from interfaces.gateway.message import ChannelType
from interfaces.gateway.response_formatter import ResponseFormatter


@pytest.fixture
def fmt():
    return ResponseFormatter()


class TestResponseFormatter:
    def test_telegram_escapes_special_chars(self, fmt):
        result = fmt.format("Hello. World!", ChannelType.TELEGRAM)
        assert r"\." in result
        assert r"\!" in result

    def test_telegram_preserves_code_blocks(self, fmt):
        result = fmt.format("Use `code.here`", ChannelType.TELEGRAM)
        assert "`code.here`" in result

    def test_discord_unchanged(self, fmt):
        text = "**bold** and _italic_"
        assert fmt.format(text, ChannelType.DISCORD) == text

    def test_slack_converts_bold(self, fmt):
        result = fmt.format("**bold**", ChannelType.SLACK)
        assert result == "*bold*"

    def test_slack_converts_italic(self, fmt):
        result = fmt.format("__italic__", ChannelType.SLACK)
        assert result == "_italic_"

    def test_email_wraps_in_paragraphs(self, fmt):
        result = fmt.format("Hello\nWorld", ChannelType.EMAIL)
        assert "<p>Hello</p>" in result
        assert "<p>World</p>" in result

    def test_whatsapp_converts_bold(self, fmt):
        result = fmt.format("**bold**", ChannelType.WHATSAPP)
        assert result == "*bold*"

    def test_imessage_plain(self, fmt):
        text = "simple text"
        assert fmt.format(text, ChannelType.IMESSAGE) == text

    def test_webchat_unchanged(self, fmt):
        text = "## Title\n- item"
        assert fmt.format(text, ChannelType.WEBCHAT) == text

    def test_voice_strips_bold(self, fmt):
        result = fmt.format("**important**", ChannelType.VOICE)
        assert "**" not in result
        assert "important" in result

    def test_voice_strips_headers(self, fmt):
        result = fmt.format("## Header\nBody text", ChannelType.VOICE)
        assert "#" not in result
        assert "Header" in result

    def test_voice_strips_code(self, fmt):
        result = fmt.format("Use `fn()` now", ChannelType.VOICE)
        assert "`" not in result

    def test_api_plain(self, fmt):
        text = "**raw** response"
        assert fmt.format(text, ChannelType.API) == text
