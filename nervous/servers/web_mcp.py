"""Web MCP Server — Brave Search + URL fetch.

Exposed tools
─────────────
  web_search    Query Brave Search API, returns top N results (title, URL, snippet).
  web_fetch     HTTP GET a URL and return the text body (truncated to max bytes).

Both tools degrade gracefully when API keys are missing or the network is
unreachable: they return a JSON error payload instead of raising.
"""

import json
import re
from typing import Any

import httpx
import structlog

from config.settings import get_settings
from core.cascade.types import ToolCall, ToolDefinition, ToolResult

from .base import BaseMCPServer

logger = structlog.get_logger(__name__)

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_BRAVE_MAX_RESULTS = 10  # hard cap accepted by the API

# ── Tool definitions ──────────────────────────────────────────────────────────

_TOOL_SEARCH = ToolDefinition(
    name="web_search",
    description=(
        "Search the web using Brave Search. Returns titles, URLs, and snippets "
        "for the top results. Use for current events or factual lookups."
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string.",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (1–10, default 5).",
                "default": 5,
                "minimum": 1,
                "maximum": 10,
            },
        },
        "required": ["query"],
    },
)

_TOOL_FETCH = ToolDefinition(
    name="web_fetch",
    description=(
        "Fetch the content of a URL and return its text body. "
        "HTML tags are stripped. Content is truncated to avoid token overflow."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Fully qualified URL to fetch (must start with http:// or https://).",
            }
        },
        "required": ["url"],
    },
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _strip_html(text: str) -> str:
    """Remove HTML/XML tags and collapse whitespace."""
    no_tags = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", no_tags).strip()


def _validate_url(url: str) -> str | None:
    """Return an error message if the URL is unsafe, else None."""
    if not url.startswith(("http://", "https://")):
        return "URL must start with http:// or https://"
    # Reject private / loopback ranges — basic SSRF mitigation
    blocked = ("localhost", "127.", "0.0.0.0", "169.254.", "::1", "10.", "192.168.", "172.")
    host = url.split("/")[2].split(":")[0].lower()
    if any(host == b or host.startswith(b) for b in blocked):
        return f"Requests to '{host}' are not allowed"
    return None


# ── Server class ──────────────────────────────────────────────────────────────


class WebMCP(BaseMCPServer):
    """Web search and URL fetch MCP server.

    Args:
        brave_api_key: Override Brave API key (tests / CI). Falls back to settings.
        timeout_s:     HTTP timeout override (seconds). Falls back to settings.
        max_bytes:     Response body size cap. Falls back to settings.
    """

    def __init__(
        self,
        brave_api_key: str | None = None,
        timeout_s: int | None = None,
        max_bytes: int | None = None,
    ) -> None:
        s = get_settings()
        self._api_key = brave_api_key if brave_api_key is not None else s.brave_api_key
        self._timeout = timeout_s if timeout_s is not None else s.mcp_fetch_timeout_s
        self._max_bytes = max_bytes if max_bytes is not None else s.mcp_fetch_max_bytes
        logger.info(
            "web_mcp_ready",
            brave_configured=bool(self._api_key),
            timeout_s=self._timeout,
            max_bytes=self._max_bytes,
        )

    @property
    def name(self) -> str:
        return "web"

    def get_tool_definitions(self) -> list[ToolDefinition]:
        return [_TOOL_SEARCH, _TOOL_FETCH]

    # ── Tool implementations ──────────────────────────────────────────────────

    async def _web_search(self, query: str, num_results: int) -> str:
        if not self._api_key:
            return json.dumps({"error": "Brave API key not configured (WORLDAI_BRAVE_API_KEY)"})

        n = max(1, min(num_results, _BRAVE_MAX_RESULTS))
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._api_key,
        }
        params: dict[str, Any] = {"q": query, "count": n}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(_BRAVE_SEARCH_URL, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.TimeoutException:
            return json.dumps({"error": "Brave Search request timed out"})
        except httpx.HTTPStatusError as exc:
            return json.dumps({"error": f"Brave Search HTTP {exc.response.status_code}"})
        except Exception as exc:  # noqa: BLE001
            logger.error("brave_search_error", error=str(exc))
            return json.dumps({"error": f"Search failed: {exc}"})

        results = []
        for item in data.get("web", {}).get("results", [])[:n]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("description", ""),
                }
            )
        return json.dumps({"query": query, "results": results, "count": len(results)})

    async def _web_fetch(self, url: str) -> str:
        err = _validate_url(url)
        if err:
            return json.dumps({"error": err})

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; WorldAI/0.1; +https://github.com/world-ai)"
            ),
            "Accept": "text/html,text/plain,application/json;q=0.9,*/*;q=0.8",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                max_redirects=5,
            ) as client:
                async with client.stream("GET", url, headers=headers) as resp:
                    resp.raise_for_status()
                    content_type = resp.headers.get("content-type", "")
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in resp.aiter_bytes(chunk_size=4096):
                        total += len(chunk)
                        chunks.append(chunk)
                        if total >= self._max_bytes:
                            break
        except httpx.TimeoutException:
            return json.dumps({"error": "Request timed out", "url": url})
        except httpx.HTTPStatusError as exc:
            return json.dumps({"error": f"HTTP {exc.response.status_code}", "url": url})
        except Exception as exc:  # noqa: BLE001
            logger.error("web_fetch_error", url=url, error=str(exc))
            return json.dumps({"error": f"Fetch failed: {exc}", "url": url})

        raw = b"".join(chunks)
        text = raw.decode("utf-8", errors="replace")
        truncated = total >= self._max_bytes

        # Strip HTML only for HTML responses
        if "html" in content_type.lower():
            text = _strip_html(text)

        return json.dumps(
            {
                "url": url,
                "content": text[: self._max_bytes],
                "content_type": content_type,
                "size_bytes": total,
                "truncated": truncated,
            }
        )

    # ── Dispatch ─────────────────────────────────────────────────────────────

    async def execute_tool(self, call: ToolCall) -> ToolResult:
        """Route *call* to the matching method; never raises."""
        args = call.arguments
        try:
            match call.name:
                case "web_search":
                    content = await self._web_search(
                        query=args["query"],
                        num_results=int(args.get("num_results", 5)),
                    )
                case "web_fetch":
                    content = await self._web_fetch(url=args["url"])
                case _:
                    return ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=json.dumps({"error": f"Unknown tool: {call.name}"}),
                        is_error=True,
                    )
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("web_mcp_bad_args", tool=call.name, error=str(exc))
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps({"error": f"Invalid arguments: {exc}"}),
                is_error=True,
            )

        logger.info("web_mcp_ok", tool=call.name)
        return ToolResult(tool_call_id=call.id, name=call.name, content=content)
