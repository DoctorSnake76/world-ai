"""Filesystem MCP Server — sandboxed read/write/list/delete operations.

Every path is resolved relative to ``WORLDAI_MCP_SANDBOX_ROOT``.  Any attempt
to escape the sandbox (via ``..`` or symlinks) raises ``SandboxViolationError``
and returns an error ToolResult — the agent never sees the real filesystem.

Exposed tools
─────────────
  fs_read_file        Read file content (UTF-8).
  fs_write_file       Write / overwrite a file (creates parent dirs).
  fs_list_directory   List entries at a given path.
  fs_file_exists      Check whether a path exists.
  fs_delete_file      Delete a single file (irreversible — risky action).
"""

import asyncio
import json
from pathlib import Path
from typing import Any

import structlog

from config.settings import get_settings
from core.cascade.types import ToolCall, ToolDefinition, ToolResult

from .base import BaseMCPServer

logger = structlog.get_logger(__name__)

_MAX_READ_BYTES = 1_048_576  # 1 MB — truncate beyond this


class SandboxViolationError(PermissionError):
    """Raised when a path resolution escapes the sandbox boundary."""


# ── Tool definitions (JSON Schema) ───────────────────────────────────────────

_TOOL_READ = ToolDefinition(
    name="fs_read_file",
    description=(
        "Read the UTF-8 content of a file inside the user sandbox. "
        "Returns the content and byte size."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path inside the sandbox (e.g. 'notes/todo.txt').",
            }
        },
        "required": ["path"],
    },
)

_TOOL_WRITE = ToolDefinition(
    name="fs_write_file",
    description=(
        "Write or overwrite a file in the user sandbox. "
        "Parent directories are created automatically."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path inside the sandbox.",
            },
            "content": {
                "type": "string",
                "description": "Full text content to write (UTF-8).",
            },
        },
        "required": ["path", "content"],
    },
)

_TOOL_LIST = ToolDefinition(
    name="fs_list_directory",
    description="List files and subdirectories at a given path inside the sandbox.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative directory path. Defaults to sandbox root if omitted.",
                "default": "",
            }
        },
        "required": [],
    },
)

_TOOL_EXISTS = ToolDefinition(
    name="fs_file_exists",
    description="Check whether a path exists inside the sandbox.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path to check.",
            }
        },
        "required": ["path"],
    },
)

_TOOL_DELETE = ToolDefinition(
    name="fs_delete_file",
    description=(
        "Permanently delete a single file from the user sandbox. "
        "WARNING: this action is irreversible."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Relative path of the file to delete.",
            }
        },
        "required": ["path"],
    },
)


# ── Server class ─────────────────────────────────────────────────────────────


class FilesystemMCP(BaseMCPServer):
    """Sandboxed filesystem MCP server.

    Args:
        sandbox_root: Override the sandbox path (used in tests).  Falls back to
                      ``settings.mcp_sandbox_root`` when *None*.
    """

    def __init__(self, sandbox_root: str | None = None) -> None:
        root = sandbox_root or get_settings().mcp_sandbox_root
        self._root = Path(root).resolve()
        # Directory is created lazily on first write to avoid errors at import time
        # when running outside Docker (e.g. during tests with a tmp_path override).
        self._root_initialised = False
        logger.info("filesystem_mcp_ready", sandbox=str(self._root))

    def _ensure_root(self) -> None:
        if not self._root_initialised:
            self._root.mkdir(parents=True, exist_ok=True)
            self._root_initialised = True

    @property
    def name(self) -> str:
        return "filesystem"

    def get_tool_definitions(self) -> list[ToolDefinition]:
        return [_TOOL_READ, _TOOL_WRITE, _TOOL_LIST, _TOOL_EXISTS, _TOOL_DELETE]

    # ── Sandbox helpers ───────────────────────────────────────────────────────

    def _resolve(self, path: str) -> Path:
        """Return the absolute ``Path`` for *path*, enforcing sandbox boundary.

        Strips leading slashes so the caller can pass either ``notes/todo.txt``
        or ``/notes/todo.txt`` interchangeably.
        """
        self._ensure_root()
        clean = path.lstrip("/")
        resolved = (self._root / clean).resolve()
        # resolve() follows symlinks — safe to compare string prefixes after
        if not str(resolved).startswith(str(self._root)):
            raise SandboxViolationError(
                f"Path '{path}' resolves outside sandbox '{self._root}'"
            )
        return resolved

    # ── Tool implementations ──────────────────────────────────────────────────

    async def _read_file(self, path: str) -> str:
        target = self._resolve(path)
        if not target.exists():
            return json.dumps({"error": f"File not found: {path}"})
        if not target.is_file():
            return json.dumps({"error": f"'{path}' is not a file"})

        raw = await asyncio.to_thread(target.read_bytes)
        truncated = len(raw) > _MAX_READ_BYTES
        content = raw[:_MAX_READ_BYTES].decode("utf-8", errors="replace")
        return json.dumps(
            {
                "path": path,
                "content": content,
                "size_bytes": len(raw),
                "truncated": truncated,
            }
        )

    async def _write_file(self, path: str, content: str) -> str:
        target = self._resolve(path)
        await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(target.write_text, content, encoding="utf-8")
        return json.dumps(
            {
                "path": path,
                "size_bytes": len(content.encode("utf-8")),
                "written": True,
            }
        )

    async def _list_directory(self, path: str) -> str:
        target = self._resolve(path)
        if not target.exists():
            return json.dumps({"error": f"Directory not found: {path}"})
        if not target.is_dir():
            return json.dumps({"error": f"'{path}' is not a directory"})

        def _scan() -> list[dict[str, Any]]:
            entries = []
            for entry in sorted(target.iterdir()):
                rel = str(entry.relative_to(self._root))
                entries.append(
                    {
                        "name": entry.name,
                        "path": rel,
                        "type": "directory" if entry.is_dir() else "file",
                        "size_bytes": entry.stat().st_size if entry.is_file() else None,
                    }
                )
            return entries

        entries = await asyncio.to_thread(_scan)
        return json.dumps({"path": path or "/", "entries": entries, "count": len(entries)})

    async def _file_exists(self, path: str) -> str:
        try:
            target = self._resolve(path)
        except SandboxViolationError:
            return json.dumps({"path": path, "exists": False})
        kind = (
            "file" if target.is_file()
            else "directory" if target.is_dir()
            else "not_found"
        )
        return json.dumps({"path": path, "exists": target.exists(), "type": kind})

    async def _delete_file(self, path: str) -> str:
        target = self._resolve(path)
        if not target.exists():
            return json.dumps({"error": f"File not found: {path}"})
        if not target.is_file():
            return json.dumps({"error": f"'{path}' is not a file (cannot delete directories)"})
        await asyncio.to_thread(target.unlink)
        logger.info("filesystem_mcp_deleted", path=path)
        return json.dumps({"path": path, "deleted": True})

    # ── Dispatch ─────────────────────────────────────────────────────────────

    async def execute_tool(self, call: ToolCall) -> ToolResult:
        """Route *call* to the matching method; never raises."""
        args = call.arguments
        try:
            match call.name:
                case "fs_read_file":
                    content = await self._read_file(args["path"])
                case "fs_write_file":
                    content = await self._write_file(args["path"], args["content"])
                case "fs_list_directory":
                    content = await self._list_directory(args.get("path", ""))
                case "fs_file_exists":
                    content = await self._file_exists(args["path"])
                case "fs_delete_file":
                    content = await self._delete_file(args["path"])
                case _:
                    return ToolResult(
                        tool_call_id=call.id,
                        name=call.name,
                        content=json.dumps({"error": f"Unknown tool: {call.name}"}),
                        is_error=True,
                    )
        except SandboxViolationError as exc:
            logger.warning("sandbox_violation", tool=call.name, error=str(exc))
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps({"error": f"Access denied: {exc}"}),
                is_error=True,
            )
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("filesystem_mcp_bad_args", tool=call.name, error=str(exc))
            return ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps({"error": f"Invalid arguments: {exc}"}),
                is_error=True,
            )

        logger.info("filesystem_mcp_ok", tool=call.name, path=args.get("path", ""))
        return ToolResult(tool_call_id=call.id, name=call.name, content=content)
