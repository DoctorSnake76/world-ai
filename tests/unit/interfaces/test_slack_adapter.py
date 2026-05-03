"""Tests for SlackAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from interfaces.adapters.base_adapter import AdapterError
from interfaces.adapters.slack_adapter import SlackAdapter
from interfaces.gateway.message import ChannelType, ConfirmationChoice


@pytest.fixture
def adapter():
    return SlackAdapter(bot_token="xoxb-test-token", signing_secret="secret123")


# ---------------------------------------------------------------------------
# receive — url_verification
# ---------------------------------------------------------------------------


class TestReceiveUrlVerification:
    async def test_challenge_returns_system_message(self, adapter):
        raw = {"type": "url_verification", "challenge": "abc123", "token": "tok"}
        msg = await adapter.receive(raw)
        assert msg.user_id == "_system"
        assert "__challenge__:abc123" == msg.content
        assert msg.channel == ChannelType.SLACK

    async def test_session_is_challenge(self, adapter):
        raw = {"type": "url_verification", "challenge": "xyz"}
        msg = await adapter.receive(raw)
        assert msg.session_id == "_challenge"


# ---------------------------------------------------------------------------
# receive — event_callback (message)
# ---------------------------------------------------------------------------


class TestReceiveEventCallback:
    def _message_event(self, text="hello", user="U1", channel="C1", thread_ts=None):
        event: dict = {"type": "message", "user": user, "channel": channel, "text": text, "ts": "1234"}
        if thread_ts:
            event["thread_ts"] = thread_ts
        return {
            "type": "event_callback",
            "event": event,
        }

    async def test_basic_message(self, adapter):
        msg = await adapter.receive(self._message_event())
        assert msg.channel == ChannelType.SLACK
        assert msg.user_id == "U1"
        assert msg.session_id == "C1"
        assert msg.content == "hello"

    async def test_thread_ts_as_reply_to(self, adapter):
        msg = await adapter.receive(self._message_event(thread_ts="9999"))
        assert msg.reply_to == "9999"

    async def test_app_mention(self, adapter):
        raw = {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "user": "U2",
                "channel": "C2",
                "text": "<@BOT> help",
                "ts": "1235",
            },
        }
        msg = await adapter.receive(raw)
        assert msg.content == "<@BOT> help"
        assert msg.user_id == "U2"

    async def test_bot_message_raises(self, adapter):
        raw = {
            "type": "event_callback",
            "event": {
                "type": "message",
                "bot_id": "B1",
                "channel": "C1",
                "text": "I am a bot",
                "ts": "1236",
            },
        }
        with pytest.raises(AdapterError, match="bot message"):
            await adapter.receive(raw)

    async def test_unsupported_event_subtype_raises(self, adapter):
        raw = {"type": "event_callback", "event": {"type": "file_share"}}
        with pytest.raises(AdapterError, match="sub-type"):
            await adapter.receive(raw)

    async def test_unsupported_top_level_type_raises(self, adapter):
        with pytest.raises(AdapterError, match="Unsupported Slack event type"):
            await adapter.receive({"type": "some_unknown_type"})


# ---------------------------------------------------------------------------
# receive — block_actions (boutons)
# ---------------------------------------------------------------------------


class TestReceiveBlockActions:
    def _block_action(self, action_id="confirm"):
        return {
            "type": "block_actions",
            "user": {"id": "U5"},
            "channel": {"id": "C5"},
            "container": {"message_ts": "ts-msg"},
            "actions": [{"action_id": action_id, "value": action_id}],
        }

    async def test_confirm_action(self, adapter):
        msg = await adapter.receive(self._block_action("confirm"))
        assert msg.is_confirmation
        assert msg.confirmation_choice == ConfirmationChoice.CONFIRM

    async def test_cancel_action(self, adapter):
        msg = await adapter.receive(self._block_action("cancel"))
        assert msg.confirmation_choice == ConfirmationChoice.CANCEL

    async def test_modify_action(self, adapter):
        msg = await adapter.receive(self._block_action("modify"))
        assert msg.confirmation_choice == ConfirmationChoice.MODIFY

    async def test_unknown_action_no_choice(self, adapter):
        msg = await adapter.receive(self._block_action("something_else"))
        assert msg.confirmation_choice is None

    async def test_no_actions_raises(self, adapter):
        raw = {"type": "block_actions", "user": {"id": "U1"}, "channel": {"id": "C1"}, "actions": []}
        with pytest.raises(AdapterError, match="no actions"):
            await adapter.receive(raw)


# ---------------------------------------------------------------------------
# send
# ---------------------------------------------------------------------------


class TestSend:
    async def test_send_calls_postmessage(self, adapter):
        original = MagicMock()
        original.metadata = {"slack_channel": "C1"}
        original.session_id = "C1"
        original.reply_to = None

        with patch.object(adapter, "_call_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {"ok": True}
            await adapter.send(original, "Hello!")
            path = mock_api.call_args[0][0]
            assert path == "/chat.postMessage"
            payload = mock_api.call_args[0][1]
            assert payload["text"] == "Hello!"
            assert payload["channel"] == "C1"

    async def test_send_threads_reply(self, adapter):
        original = MagicMock()
        original.metadata = {"slack_channel": "C1"}
        original.session_id = "C1"
        original.reply_to = "thread-ts"

        with patch.object(adapter, "_call_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {"ok": True}
            await adapter.send(original, "Reply!")
            payload = mock_api.call_args[0][1]
            assert payload["thread_ts"] == "thread-ts"

    async def test_send_without_token_raises(self):
        adapter = SlackAdapter(bot_token="", signing_secret="")
        original = MagicMock()
        original.metadata = {}
        original.session_id = "C1"
        original.reply_to = None
        with pytest.raises(AdapterError, match="BOT_TOKEN"):
            await adapter.send(original, "hi")


# ---------------------------------------------------------------------------
# send_confirmation
# ---------------------------------------------------------------------------


class TestSendConfirmation:
    async def test_sends_blocks(self, adapter):
        original = MagicMock()
        original.metadata = {"slack_channel": "C1"}
        original.session_id = "C1"
        original.reply_to = None

        with patch.object(adapter, "_call_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {"ok": True}
            await adapter.send_confirmation(original, "Confirm?")
            payload = mock_api.call_args[0][1]
            assert "blocks" in payload
            action_block = payload["blocks"][1]
            assert action_block["type"] == "actions"
            assert len(action_block["elements"]) == 3

    async def test_custom_choices(self, adapter):
        original = MagicMock()
        original.metadata = {"slack_channel": "C1"}
        original.session_id = "C1"
        original.reply_to = None

        with patch.object(adapter, "_call_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {"ok": True}
            await adapter.send_confirmation(
                original,
                "Delete?",
                choices=[ConfirmationChoice.CONFIRM, ConfirmationChoice.CANCEL],
            )
            action_block = mock_api.call_args[0][1]["blocks"][1]
            assert len(action_block["elements"]) == 2


# ---------------------------------------------------------------------------
# _call_api errors
# ---------------------------------------------------------------------------


class TestCallApiErrors:
    async def test_slack_api_ok_false_raises(self, adapter):
        with patch.object(adapter, "_get_client", new_callable=AsyncMock) as mock_client:
            resp = MagicMock()
            resp.json.return_value = {"ok": False, "error": "channel_not_found"}
            resp.raise_for_status = MagicMock()
            client = AsyncMock()
            client.post.return_value = resp
            mock_client.return_value = client

            with pytest.raises(AdapterError, match="channel_not_found"):
                await adapter._call_api("/chat.postMessage", {})

    async def test_http_error_raises(self, adapter):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        exc = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_resp)

        with patch.object(adapter, "_get_client", new_callable=AsyncMock) as mock_client:
            client = AsyncMock()
            client.post.side_effect = exc
            mock_client.return_value = client

            with pytest.raises(AdapterError, match="500"):
                await adapter._call_api("/chat.postMessage", {})
