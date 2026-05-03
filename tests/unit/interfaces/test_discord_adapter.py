"""Tests for DiscordAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from interfaces.adapters.base_adapter import AdapterError
from interfaces.adapters.discord_adapter import DiscordAdapter
from interfaces.gateway.message import ChannelType, ConfirmationChoice


@pytest.fixture
def adapter():
    return DiscordAdapter(token="Bot-test-token", app_id="123456789", public_key="")


# ---------------------------------------------------------------------------
# receive — PING
# ---------------------------------------------------------------------------


class TestReceivePing:
    async def test_ping_returns_system_message(self, adapter):
        raw = {"type": 1}
        msg = await adapter.receive(raw)
        assert msg.user_id == "_system"
        assert msg.content == "__ping__"
        assert msg.channel == ChannelType.DISCORD

    async def test_ping_session_is_ping(self, adapter):
        msg = await adapter.receive({"type": 1})
        assert msg.session_id == "_ping"


# ---------------------------------------------------------------------------
# receive — Slash command (APPLICATION_COMMAND)
# ---------------------------------------------------------------------------


class TestReceiveSlashCommand:
    def _slash_raw(self, user_id="42", guild="111", channel="222", options=None):
        if options is None:
            options = [{"type": 3, "name": "query", "value": "hello"}]
        return {
            "type": 2,
            "id": "interaction-id",
            "token": "interaction-token",
            "application_id": "app-id",
            "guild_id": guild,
            "channel_id": channel,
            "member": {"user": {"id": user_id}},
            "data": {"name": "ask", "options": options},
        }

    async def test_basic_slash(self, adapter):
        msg = await adapter.receive(self._slash_raw())
        assert msg.channel == ChannelType.DISCORD
        assert msg.user_id == "42"
        assert msg.session_id == "111:222"
        assert msg.content == "hello"

    async def test_metadata_contains_interaction_token(self, adapter):
        msg = await adapter.receive(self._slash_raw())
        assert msg.metadata["interaction_token"] == "interaction-token"
        assert msg.metadata["interaction_id"] == "interaction-id"

    async def test_no_options_uses_command_name(self, adapter):
        raw = self._slash_raw(options=[])
        msg = await adapter.receive(raw)
        assert msg.content == "ask"

    async def test_missing_user_raises(self, adapter):
        raw = {
            "type": 2,
            "guild_id": "1",
            "channel_id": "2",
            "data": {"name": "cmd"},
        }
        with pytest.raises(AdapterError):
            await adapter.receive(raw)


# ---------------------------------------------------------------------------
# receive — Message component (button)
# ---------------------------------------------------------------------------


class TestReceiveMessageComponent:
    def _component_raw(self, custom_id="confirm"):
        return {
            "type": 3,
            "id": "cid",
            "token": "ctok",
            "application_id": "app-id",
            "guild_id": "g1",
            "channel_id": "c1",
            "member": {"user": {"id": "99"}},
            "data": {"custom_id": custom_id, "component_type": 2},
        }

    async def test_confirm_button(self, adapter):
        msg = await adapter.receive(self._component_raw("confirm"))
        assert msg.is_confirmation
        assert msg.confirmation_choice == ConfirmationChoice.CONFIRM

    async def test_cancel_button(self, adapter):
        msg = await adapter.receive(self._component_raw("cancel"))
        assert msg.confirmation_choice == ConfirmationChoice.CANCEL

    async def test_modify_button(self, adapter):
        msg = await adapter.receive(self._component_raw("modify"))
        assert msg.confirmation_choice == ConfirmationChoice.MODIFY

    async def test_unknown_custom_id_no_choice(self, adapter):
        msg = await adapter.receive(self._component_raw("random_action"))
        assert msg.confirmation_choice is None


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------


class TestSend:
    async def test_send_via_followup_when_token_present(self, adapter):
        original = MagicMock()
        original.metadata = {"interaction_token": "tok", "app_id": "app123", "channel_id": "c1"}
        original.user_id = "u1"

        with patch.object(adapter, "_call_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {}
            await adapter.send(original, "hello")
            path = mock_api.call_args[0][1]
            assert "webhooks" in path

    async def test_send_via_channel_when_no_token(self, adapter):
        original = MagicMock()
        original.metadata = {"interaction_token": None, "app_id": None, "channel_id": "c99"}
        original.user_id = "u1"
        original.session_id = "g:c99"

        with patch.object(adapter, "_call_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {}
            await adapter.send(original, "hi")
            path = mock_api.call_args[0][1]
            assert "/channels/c99/messages" in path

    async def test_send_without_token_raises(self):
        adapter = DiscordAdapter(token="", app_id="", public_key="")
        original = MagicMock()
        original.metadata = {"interaction_token": None, "app_id": None, "channel_id": "c1"}
        original.user_id = "u1"
        original.session_id = "g:c1"

        with pytest.raises(AdapterError, match="BOT_TOKEN"):
            await adapter.send(original, "hi")


# ---------------------------------------------------------------------------
# send_confirmation
# ---------------------------------------------------------------------------


class TestSendConfirmation:
    async def test_sends_components(self, adapter):
        original = MagicMock()
        original.metadata = {"interaction_token": "tok", "app_id": "app1", "channel_id": "c1"}
        original.user_id = "u1"

        with patch.object(adapter, "_call_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {}
            await adapter.send_confirmation(original, "Confirm?")
            payload = mock_api.call_args[0][2]
            assert "components" in payload
            row = payload["components"][0]
            assert row["type"] == 1  # ACTION_ROW
            assert len(row["components"]) == 3  # 3 default choices

    async def test_custom_choices(self, adapter):
        original = MagicMock()
        original.metadata = {"interaction_token": "tok", "app_id": "app1", "channel_id": "c1"}
        original.user_id = "u1"

        with patch.object(adapter, "_call_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {}
            await adapter.send_confirmation(
                original,
                "Delete?",
                choices=[ConfirmationChoice.CONFIRM, ConfirmationChoice.CANCEL],
            )
            row = mock_api.call_args[0][2]["components"][0]
            assert len(row["components"]) == 2


# ---------------------------------------------------------------------------
# _call_api errors
# ---------------------------------------------------------------------------


class TestCallApiErrors:
    async def test_http_error_raises_adapter_error(self, adapter):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"
        exc = httpx.HTTPStatusError("403", request=MagicMock(), response=mock_resp)

        with patch.object(adapter, "_get_client", new_callable=AsyncMock) as mock_client:
            client = AsyncMock()
            client.post.side_effect = exc
            mock_client.return_value = client

            with pytest.raises(AdapterError, match="403"):
                await adapter._call_api("POST", "/channels/1/messages", {})

    async def test_request_error_raises_adapter_error(self, adapter):
        exc = httpx.RequestError("timeout", request=MagicMock())

        with patch.object(adapter, "_get_client", new_callable=AsyncMock) as mock_client:
            client = AsyncMock()
            client.post.side_effect = exc
            mock_client.return_value = client

            with pytest.raises(AdapterError, match="request failed"):
                await adapter._call_api("POST", "/channels/1/messages", {})
