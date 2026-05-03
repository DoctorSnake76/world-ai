"""Tests for BaseAdapter contract enforcement."""

import pytest
from interfaces.adapters.base_adapter import AdapterError, BaseAdapter
from interfaces.gateway.message import ChannelType, ConfirmationChoice, UnifiedMessage


# ---------------------------------------------------------------------------
# Concrete stub for testing
# ---------------------------------------------------------------------------


class StubAdapter(BaseAdapter):
    channel = ChannelType.API

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.confirmations: list[str] = []

    async def receive(self, raw: dict) -> UnifiedMessage:
        return UnifiedMessage.text(
            channel=self.channel,
            user_id=raw["user"],
            session_id=raw.get("session", "s1"),
            content=raw["text"],
        )

    async def send(self, original: UnifiedMessage, response_text: str) -> None:
        self.sent.append(response_text)

    async def send_confirmation(self, original, prompt, choices=None) -> None:
        self.confirmations.append(prompt)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBaseAdapterContract:
    def test_missing_channel_raises(self):
        with pytest.raises(TypeError, match="channel: ChannelType"):

            class BadAdapter(BaseAdapter):
                async def receive(self, raw): ...
                async def send(self, original, response_text): ...
                async def send_confirmation(self, original, prompt, choices=None): ...

    def test_channel_wrong_type_raises(self):
        with pytest.raises(TypeError, match="channel: ChannelType"):

            class BadAdapter(BaseAdapter):
                channel = "telegram"  # string instead of ChannelType

                async def receive(self, raw): ...
                async def send(self, original, response_text): ...
                async def send_confirmation(self, original, prompt, choices=None): ...

    def test_valid_concrete_adapter(self):
        adapter = StubAdapter()
        assert adapter.channel == ChannelType.API

    async def test_receive_returns_unified_message(self):
        adapter = StubAdapter()
        msg = await adapter.receive({"user": "u1", "text": "hello"})
        assert isinstance(msg, UnifiedMessage)
        assert msg.user_id == "u1"
        assert msg.content == "hello"
        assert msg.channel == ChannelType.API

    async def test_send_called(self):
        adapter = StubAdapter()
        msg = UnifiedMessage.text(ChannelType.API, "u", "s", "hi")
        await adapter.send(msg, "response!")
        assert adapter.sent == ["response!"]

    async def test_send_confirmation_called(self):
        adapter = StubAdapter()
        msg = UnifiedMessage.text(ChannelType.API, "u", "s", "hi")
        await adapter.send_confirmation(msg, "Confirm?")
        assert adapter.confirmations == ["Confirm?"]

    def test_default_choices_returns_all(self):
        adapter = StubAdapter()
        choices = adapter.default_choices()
        assert ConfirmationChoice.CONFIRM in choices
        assert ConfirmationChoice.MODIFY in choices
        assert ConfirmationChoice.CANCEL in choices
        assert len(choices) == 3

    def test_adapter_error_is_exception(self):
        err = AdapterError("boom")
        assert isinstance(err, Exception)
        assert str(err) == "boom"

    def test_abstract_methods_enforced(self):
        with pytest.raises(TypeError):

            class IncompleteAdapter(BaseAdapter):
                channel = ChannelType.DISCORD
                # missing receive, send, send_confirmation

            IncompleteAdapter()
