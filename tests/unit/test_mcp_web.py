"""Unit tests for WebMCP — Brave search and URL fetch (mocked network)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.cascade.types import ToolCall
from nervous.servers.web_mcp import WebMCP, _strip_html, _validate_url


def make_call(name: str, **kwargs) -> ToolCall:
    return ToolCall(id="test-id", name=name, arguments=kwargs)


# ── Helpers ───────────────────────────────────────────────────────────────────


class TestHelpers:
    def test_strip_html_removes_tags(self) -> None:
        assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_strip_html_collapses_whitespace(self) -> None:
        result = _strip_html("<div>  foo   bar  </div>")
        assert result == "foo bar"

    def test_strip_html_plain_text_unchanged(self) -> None:
        assert _strip_html("plain text") == "plain text"

    def test_validate_url_valid_https(self) -> None:
        assert _validate_url("https://example.com/path") is None

    def test_validate_url_valid_http(self) -> None:
        assert _validate_url("http://example.com") is None

    def test_validate_url_missing_scheme(self) -> None:
        assert _validate_url("example.com") is not None

    def test_validate_url_ftp_blocked(self) -> None:
        assert _validate_url("ftp://example.com") is not None

    def test_validate_url_localhost_blocked(self) -> None:
        assert _validate_url("http://localhost/admin") is not None

    def test_validate_url_loopback_blocked(self) -> None:
        assert _validate_url("http://127.0.0.1/secret") is not None

    def test_validate_url_private_10_blocked(self) -> None:
        assert _validate_url("http://10.0.0.1/") is not None

    def test_validate_url_private_192_blocked(self) -> None:
        assert _validate_url("http://192.168.1.100/") is not None

    def test_validate_url_metadata_blocked(self) -> None:
        assert _validate_url("http://169.254.169.254/metadata") is not None


# ── WebMCP init ───────────────────────────────────────────────────────────────


class TestWebMCPInit:
    def test_server_name(self) -> None:
        w = WebMCP(brave_api_key="key", timeout_s=10, max_bytes=1024)
        assert w.name == "web"

    def test_has_two_tools(self) -> None:
        w = WebMCP(brave_api_key="key", timeout_s=10, max_bytes=1024)
        assert len(w.get_tool_definitions()) == 2

    def test_tool_names(self) -> None:
        w = WebMCP()
        names = {td.name for td in w.get_tool_definitions()}
        assert names == {"web_search", "web_fetch"}


# ── web_search ────────────────────────────────────────────────────────────────


class TestWebSearch:
    def _make_brave_response(self, n: int = 3) -> dict:
        return {
            "web": {
                "results": [
                    {
                        "title": f"Result {i}",
                        "url": f"https://example.com/{i}",
                        "description": f"Snippet {i}",
                    }
                    for i in range(n)
                ]
            }
        }

    async def test_search_no_api_key_returns_error(self) -> None:
        w = WebMCP(brave_api_key="")
        result = await w.execute_tool(make_call("web_search", query="test"))
        data = json.loads(result.content)
        assert "error" in data
        assert "WORLDAI_BRAVE_API_KEY" in data["error"]

    async def test_search_returns_results(self) -> None:
        w = WebMCP(brave_api_key="fake-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = self._make_brave_response(3)
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await w.execute_tool(make_call("web_search", query="hello", num_results=3))

        data = json.loads(result.content)
        assert data["count"] == 3
        assert data["results"][0]["title"] == "Result 0"
        assert data["results"][0]["url"] == "https://example.com/0"

    async def test_search_caps_results_at_10(self) -> None:
        w = WebMCP(brave_api_key="fake-key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = self._make_brave_response(5)
        mock_resp.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            # num_results=99 should be capped to 10 before the request
            result = await w.execute_tool(make_call("web_search", query="q", num_results=99))

        assert not result.is_error

    async def test_search_timeout_returns_error(self) -> None:
        import httpx

        w = WebMCP(brave_api_key="fake-key")
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client_cls.return_value = mock_client

            result = await w.execute_tool(make_call("web_search", query="q"))

        data = json.loads(result.content)
        assert "timed out" in data["error"].lower()

    async def test_search_missing_query_returns_error(self) -> None:
        w = WebMCP(brave_api_key="key")
        call = ToolCall(id="t", name="web_search", arguments={})
        result = await w.execute_tool(call)
        assert result.is_error


# ── web_fetch ─────────────────────────────────────────────────────────────────


class TestWebFetch:
    def _make_stream_mock(self, body: bytes, content_type: str = "text/html") -> MagicMock:
        """Build a mock for httpx streaming response."""
        async def _iter_bytes(chunk_size=4096):
            yield body

        mock_resp = MagicMock()
        mock_resp.headers = {"content-type": content_type}
        mock_resp.raise_for_status = MagicMock()
        mock_resp.aiter_bytes = _iter_bytes
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)
        return mock_resp

    async def test_fetch_returns_text_content(self) -> None:
        w = WebMCP(max_bytes=1024)
        html = b"<html><body><p>Hello world</p></body></html>"
        mock_resp = self._make_stream_mock(html)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.stream = MagicMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await w.execute_tool(
                make_call("web_fetch", url="https://example.com")
            )

        assert not result.is_error
        data = json.loads(result.content)
        assert "Hello world" in data["content"]
        assert data["url"] == "https://example.com"

    async def test_fetch_strips_html(self) -> None:
        w = WebMCP(max_bytes=4096)
        html = b"<div class='x'><p>Clean text</p></div>"
        mock_resp = self._make_stream_mock(html, "text/html; charset=utf-8")

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.stream = MagicMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await w.execute_tool(make_call("web_fetch", url="https://x.com"))

        data = json.loads(result.content)
        assert "<" not in data["content"]
        assert "Clean text" in data["content"]

    async def test_fetch_blocks_localhost(self) -> None:
        w = WebMCP()
        result = await w.execute_tool(
            make_call("web_fetch", url="http://localhost/admin")
        )
        data = json.loads(result.content)
        assert "error" in data
        assert not result.is_error  # graceful, not exception

    async def test_fetch_blocks_private_ip(self) -> None:
        w = WebMCP()
        result = await w.execute_tool(
            make_call("web_fetch", url="http://192.168.1.1/")
        )
        data = json.loads(result.content)
        assert "error" in data

    async def test_fetch_timeout_returns_error(self) -> None:
        import httpx

        w = WebMCP()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.__aenter__ = AsyncMock(side_effect=httpx.TimeoutException("t"))
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.stream = MagicMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            result = await w.execute_tool(
                make_call("web_fetch", url="https://slow.example.com")
            )

        data = json.loads(result.content)
        assert "timed out" in data["error"].lower()

    async def test_fetch_missing_url_returns_error(self) -> None:
        w = WebMCP()
        call = ToolCall(id="t", name="web_fetch", arguments={})
        result = await w.execute_tool(call)
        assert result.is_error


# ── Unknown tool ──────────────────────────────────────────────────────────────


class TestUnknownTool:
    async def test_unknown_returns_error(self) -> None:
        w = WebMCP()
        result = await w.execute_tool(ToolCall(id="x", name="web_fly", arguments={}))
        assert result.is_error
        assert "Unknown tool" in result.content
