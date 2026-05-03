"""Tests for the Multi-Channel Gateway (FastAPI)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from interfaces.adapters.base_adapter import BaseAdapter
from interfaces.gateway.gateway import (
    _adapters,
    app,
    register_adapter,
    set_agent_dispatch,
)
from interfaces.gateway.message import ChannelType, ConfirmationChoice, UnifiedMessage


# ---------------------------------------------------------------------------
# Stub adapter
# ---------------------------------------------------------------------------


class StubTelegramAdapter(BaseAdapter):
    channel = ChannelType.TELEGRAM

    def __init__(self) -> None:
        self.received_raw: list[dict] = []
        self.sent_texts: list[str] = []

    async def receive(self, raw: dict) -> UnifiedMessage:
        self.received_raw.append(raw)
        return UnifiedMessage.text(
            channel=ChannelType.TELEGRAM,
            user_id=str(raw.get("user_id", "anon")),
            session_id=str(raw.get("chat_id", "sess")),
            content=raw.get("text", ""),
        )

    async def send(self, original: UnifiedMessage, response_text: str) -> None:
        self.sent_texts.append(response_text)

    async def send_confirmation(self, original, prompt, choices=None) -> None:
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_adapters():
    """Isole chaque test — vide le registre et le dispatch."""
    _adapters.clear()
    set_agent_dispatch(None)
    yield
    _adapters.clear()
    set_agent_dispatch(None)


@pytest.fixture
def stub_adapter():
    adapter = StubTelegramAdapter()
    register_adapter(adapter)
    return adapter


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGatewayHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_list_channels_empty(self, client):
        resp = client.get("/channels")
        assert resp.json()["channels"] == []

    def test_list_channels_with_adapter(self, client, stub_adapter):
        resp = client.get("/channels")
        assert "telegram" in resp.json()["channels"]


class TestGatewayWebhook:
    def test_unknown_channel_returns_400(self, client):
        resp = client.post("/webhook/fax", json={"text": "hello"})
        assert resp.status_code == 400

    def test_no_adapter_returns_404(self, client):
        resp = client.post("/webhook/telegram", json={"text": "hi"})
        assert resp.status_code == 404

    def test_invalid_json_returns_422(self, client, stub_adapter):
        resp = client.post(
            "/webhook/telegram",
            data="not-json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_valid_webhook_returns_ok(self, client, stub_adapter):
        set_agent_dispatch(lambda msg: "agent reply")
        resp = client.post(
            "/webhook/telegram",
            json={"user_id": "42", "chat_id": "c1", "text": "hello"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_adapter_receives_raw_payload(self, client, stub_adapter):
        set_agent_dispatch(lambda msg: "ok")
        client.post(
            "/webhook/telegram",
            json={"user_id": "7", "text": "test msg"},
        )
        assert len(stub_adapter.received_raw) == 1
        assert stub_adapter.received_raw[0]["text"] == "test msg"

    def test_adapter_receives_formatted_response(self, client, stub_adapter):
        set_agent_dispatch(lambda msg: "**bold reply**")
        client.post("/webhook/telegram", json={"user_id": "u", "text": "hi"})
        # Telegram formatter escapes special chars
        assert len(stub_adapter.sent_texts) == 1
        # bold markers are not escaped (no special TG chars in **)
        assert "bold reply" in stub_adapter.sent_texts[0]

    def test_no_agent_dispatch_returns_stub_response(self, client, stub_adapter):
        resp = client.post("/webhook/telegram", json={"user_id": "u", "text": "ping"})
        assert resp.status_code == 200
        assert len(stub_adapter.sent_texts) == 1
        assert "not configured" in stub_adapter.sent_texts[0]


class TestGatewayPostMessage:
    def test_post_message_valid(self, client):
        set_agent_dispatch(lambda msg: "direct reply")
        resp = client.post(
            "/message",
            json={
                "channel": "api",
                "user_id": "u1",
                "session_id": "s1",
                "content": "hello",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["response"] == "direct reply"
        assert resp.json()["channel"] == "api"

    def test_post_message_invalid_body(self, client):
        resp = client.post("/message", json={"channel": "unknown"})
        assert resp.status_code == 422


class TestRegisterAdapter:
    def test_register_adds_to_registry(self):
        adapter = StubTelegramAdapter()
        register_adapter(adapter)
        assert ChannelType.TELEGRAM in _adapters

    def test_register_overwrites(self):
        a1 = StubTelegramAdapter()
        a2 = StubTelegramAdapter()
        register_adapter(a1)
        register_adapter(a2)
        assert _adapters[ChannelType.TELEGRAM] is a2
