"""Tests for WebChatAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from interfaces.adapters.base_adapter import AdapterError
from interfaces.adapters.webchat_adapter import (
    WebChatAdapter,
    _active_connections,
    register_connection,
    unregister_connection,
    list_active_sessions,
)
from interfaces.gateway.message import ChannelType, ConfirmationChoice


@pytest.fixture(autouse=True)
def clear_connections():
    _active_connections.clear()
    yield
    _active_connections.clear()


@pytest.fixture
def adapter():
    return WebChatAdapter(jwt_secret="test-secret")


# ---------------------------------------------------------------------------
# receive
# ---------------------------------------------------------------------------


class TestReceive:
    async def test_basic_message(self, adapter):
        raw = {"user_id": "u1", "content": "hello", "session_id": "sess-abc"}
        msg = await adapter.receive(raw)
        assert msg.channel == ChannelType.WEBCHAT
        assert msg.user_id == "u1"
        assert msg.session_id == "sess-abc"
        assert msg.content == "hello"

    async def test_auto_generates_session_id(self, adapter):
        raw = {"user_id": "u2", "content": "hi"}
        msg = await adapter.receive(raw)
        assert msg.session_id  # doit être non-vide
        assert len(msg.session_id) == 36  # UUID format

    async def test_missing_user_id_raises(self, adapter):
        with pytest.raises(AdapterError, match="user_id"):
            await adapter.receive({"content": "hello"})

    async def test_empty_content_allowed(self, adapter):
        msg = await adapter.receive({"user_id": "u3", "session_id": "s3"})
        assert msg.content == ""

    async def test_confirmation_choice_parsed(self, adapter):
        msg = await adapter.receive(
            {"user_id": "u1", "session_id": "s1", "content": "", "choice": "confirm"}
        )
        assert msg.is_confirmation
        assert msg.confirmation_choice == ConfirmationChoice.CONFIRM

    async def test_modify_choice(self, adapter):
        msg = await adapter.receive(
            {"user_id": "u1", "session_id": "s1", "content": "", "choice": "modify"}
        )
        assert msg.confirmation_choice == ConfirmationChoice.MODIFY

    async def test_invalid_choice_ignored(self, adapter):
        msg = await adapter.receive(
            {"user_id": "u1", "session_id": "s1", "content": "hi", "choice": "unknown"}
        )
        assert msg.confirmation_choice is None

    async def test_case_insensitive_choice(self, adapter):
        msg = await adapter.receive(
            {"user_id": "u1", "session_id": "s1", "content": "", "choice": "CANCEL"}
        )
        assert msg.confirmation_choice == ConfirmationChoice.CANCEL


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------


class TestSend:
    async def test_send_to_active_connection(self, adapter):
        ws = AsyncMock()
        register_connection("sess-1", ws)

        original = MagicMock()
        original.session_id = "sess-1"

        await adapter.send(original, "Hello there!")
        ws.send_json.assert_called_once()
        payload = ws.send_json.call_args[0][0]
        assert payload["type"] == "message"
        assert payload["content"] == "Hello there!"
        assert payload["session_id"] == "sess-1"

    async def test_send_no_connection_logs_warning(self, adapter):
        original = MagicMock()
        original.session_id = "nonexistent-session"
        # Should not raise
        await adapter.send(original, "Hello?")

    async def test_send_error_raises_adapter_error(self, adapter):
        ws = AsyncMock()
        ws.send_json.side_effect = Exception("WebSocket closed")
        register_connection("sess-err", ws)

        original = MagicMock()
        original.session_id = "sess-err"

        with pytest.raises(AdapterError, match="WebSocket send failed"):
            await adapter.send(original, "hi")

        # Connection should be unregistered on error
        assert "sess-err" not in _active_connections


# ---------------------------------------------------------------------------
# send_confirmation
# ---------------------------------------------------------------------------


class TestSendConfirmation:
    async def test_sends_confirmation_payload(self, adapter):
        ws = AsyncMock()
        register_connection("sess-conf", ws)

        original = MagicMock()
        original.session_id = "sess-conf"

        await adapter.send_confirmation(original, "Proceed?")
        ws.send_json.assert_called_once()
        payload = ws.send_json.call_args[0][0]
        assert payload["type"] == "confirmation"
        assert payload["prompt"] == "Proceed?"
        assert len(payload["choices"]) == 3

    async def test_custom_choices(self, adapter):
        ws = AsyncMock()
        register_connection("sess-cust", ws)

        original = MagicMock()
        original.session_id = "sess-cust"

        await adapter.send_confirmation(
            original,
            "Delete?",
            choices=[ConfirmationChoice.CONFIRM, ConfirmationChoice.CANCEL],
        )
        payload = ws.send_json.call_args[0][0]
        assert len(payload["choices"]) == 2
        ids = [c["id"] for c in payload["choices"]]
        assert "confirm" in ids
        assert "cancel" in ids
        assert "modify" not in ids

    async def test_send_conf_no_connection(self, adapter):
        original = MagicMock()
        original.session_id = "gone"
        # Should not raise
        await adapter.send_confirmation(original, "gone?")


# ---------------------------------------------------------------------------
# Connection registry
# ---------------------------------------------------------------------------


class TestConnectionRegistry:
    def test_register_and_list(self):
        ws = MagicMock()
        register_connection("s1", ws)
        assert "s1" in list_active_sessions()

    def test_unregister(self):
        ws = MagicMock()
        register_connection("s2", ws)
        unregister_connection("s2")
        assert "s2" not in list_active_sessions()

    def test_unregister_nonexistent_no_error(self):
        unregister_connection("doesnotexist")

    def test_on_connect_on_disconnect(self, adapter):
        ws = MagicMock()
        adapter.on_connect("sess-test", ws)
        assert "sess-test" in list_active_sessions()
        adapter.on_disconnect("sess-test")
        assert "sess-test" not in list_active_sessions()
