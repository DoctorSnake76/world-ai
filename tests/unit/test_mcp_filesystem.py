"""Unit tests for FilesystemMCP — sandbox enforcement + all CRUD tools."""

import json
from pathlib import Path

import pytest

from core.cascade.types import ToolCall
from nervous.servers.filesystem_mcp import FilesystemMCP, SandboxViolationError


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    return tmp_path / "sandbox"


@pytest.fixture
def fs(sandbox: Path) -> FilesystemMCP:
    return FilesystemMCP(sandbox_root=str(sandbox))


def make_call(name: str, **kwargs) -> ToolCall:
    return ToolCall(id="test-id", name=name, arguments=kwargs)


# ── Sandbox enforcement ───────────────────────────────────────────────────────


class TestSandboxEnforcement:
    def test_resolve_normal_path(self, fs: FilesystemMCP, sandbox: Path) -> None:
        result = fs._resolve("notes/todo.txt")
        assert result == sandbox / "notes" / "todo.txt"

    def test_resolve_strips_leading_slash(self, fs: FilesystemMCP, sandbox: Path) -> None:
        assert fs._resolve("/notes/todo.txt") == fs._resolve("notes/todo.txt")

    def test_resolve_traversal_raises(self, fs: FilesystemMCP) -> None:
        with pytest.raises(SandboxViolationError):
            fs._resolve("../../etc/passwd")

    def test_resolve_leading_slash_treated_as_relative(
        self, fs: FilesystemMCP, sandbox: Path
    ) -> None:
        # Leading slash is stripped — /etc/passwd becomes {sandbox}/etc/passwd (safe)
        result = fs._resolve("/etc/passwd")
        assert str(result).startswith(str(sandbox))

    def test_resolve_dotdot_nested_raises(self, fs: FilesystemMCP) -> None:
        with pytest.raises(SandboxViolationError):
            fs._resolve("a/b/c/../../../../../../../etc/hosts")

    def test_resolve_valid_nested(self, fs: FilesystemMCP, sandbox: Path) -> None:
        result = fs._resolve("a/b/c.txt")
        assert str(result).startswith(str(sandbox))


# ── fs_read_file ──────────────────────────────────────────────────────────────


class TestReadFile:
    async def test_read_existing_file(self, fs: FilesystemMCP, sandbox: Path) -> None:
        sandbox.mkdir(parents=True, exist_ok=True)
        (sandbox / "hello.txt").write_text("world", encoding="utf-8")
        result = await fs.execute_tool(make_call("fs_read_file", path="hello.txt"))
        assert not result.is_error
        data = json.loads(result.content)
        assert data["content"] == "world"
        assert data["size_bytes"] == 5
        assert data["truncated"] is False

    async def test_read_missing_file_returns_error(self, fs: FilesystemMCP) -> None:
        result = await fs.execute_tool(make_call("fs_read_file", path="ghost.txt"))
        assert not result.is_error  # tool-level error, not is_error
        data = json.loads(result.content)
        assert "error" in data

    async def test_read_directory_returns_error(self, fs: FilesystemMCP, sandbox: Path) -> None:
        subdir = sandbox / "adir"
        subdir.mkdir(parents=True, exist_ok=True)
        result = await fs.execute_tool(make_call("fs_read_file", path="adir"))
        data = json.loads(result.content)
        assert "error" in data

    async def test_read_traversal_blocked(self, fs: FilesystemMCP) -> None:
        result = await fs.execute_tool(
            make_call("fs_read_file", path="../../etc/passwd")
        )
        assert result.is_error
        data = json.loads(result.content)
        assert "Access denied" in data["error"]

    async def test_read_missing_arg_returns_error(self, fs: FilesystemMCP) -> None:
        call = ToolCall(id="t", name="fs_read_file", arguments={})
        result = await fs.execute_tool(call)
        assert result.is_error


# ── fs_write_file ─────────────────────────────────────────────────────────────


class TestWriteFile:
    async def test_write_creates_file(self, fs: FilesystemMCP, sandbox: Path) -> None:
        result = await fs.execute_tool(
            make_call("fs_write_file", path="new.txt", content="hello world")
        )
        assert not result.is_error
        assert (sandbox / "new.txt").read_text() == "hello world"

    async def test_write_creates_parent_dirs(self, fs: FilesystemMCP, sandbox: Path) -> None:
        await fs.execute_tool(
            make_call("fs_write_file", path="a/b/c/deep.txt", content="deep")
        )
        assert (sandbox / "a" / "b" / "c" / "deep.txt").exists()

    async def test_write_overwrites_existing(self, fs: FilesystemMCP, sandbox: Path) -> None:
        sandbox.mkdir(parents=True, exist_ok=True)
        (sandbox / "f.txt").write_text("old", encoding="utf-8")
        await fs.execute_tool(make_call("fs_write_file", path="f.txt", content="new"))
        assert (sandbox / "f.txt").read_text() == "new"

    async def test_write_traversal_blocked(self, fs: FilesystemMCP) -> None:
        result = await fs.execute_tool(
            make_call("fs_write_file", path="../../evil.txt", content="x")
        )
        assert result.is_error

    async def test_write_returns_size(self, fs: FilesystemMCP) -> None:
        result = await fs.execute_tool(
            make_call("fs_write_file", path="size.txt", content="abc")
        )
        data = json.loads(result.content)
        assert data["size_bytes"] == 3
        assert data["written"] is True


# ── fs_list_directory ─────────────────────────────────────────────────────────


class TestListDirectory:
    async def test_list_root(self, fs: FilesystemMCP, sandbox: Path) -> None:
        sandbox.mkdir(parents=True, exist_ok=True)
        (sandbox / "a.txt").write_text("a")
        (sandbox / "b.txt").write_text("b")
        result = await fs.execute_tool(make_call("fs_list_directory", path=""))
        data = json.loads(result.content)
        names = [e["name"] for e in data["entries"]]
        assert "a.txt" in names
        assert "b.txt" in names

    async def test_list_missing_dir_returns_error(self, fs: FilesystemMCP) -> None:
        result = await fs.execute_tool(make_call("fs_list_directory", path="ghost/"))
        data = json.loads(result.content)
        assert "error" in data

    async def test_list_file_as_dir_returns_error(self, fs: FilesystemMCP, sandbox: Path) -> None:
        sandbox.mkdir(parents=True, exist_ok=True)
        (sandbox / "file.txt").write_text("x")
        result = await fs.execute_tool(make_call("fs_list_directory", path="file.txt"))
        data = json.loads(result.content)
        assert "error" in data

    async def test_list_entries_have_type(self, fs: FilesystemMCP, sandbox: Path) -> None:
        sandbox.mkdir(parents=True, exist_ok=True)
        (sandbox / "notes").mkdir()
        (sandbox / "readme.md").write_text("hi")
        result = await fs.execute_tool(make_call("fs_list_directory", path=""))
        data = json.loads(result.content)
        types = {e["name"]: e["type"] for e in data["entries"]}
        assert types["notes"] == "directory"
        assert types["readme.md"] == "file"


# ── fs_file_exists ────────────────────────────────────────────────────────────


class TestFileExists:
    async def test_exists_true(self, fs: FilesystemMCP, sandbox: Path) -> None:
        sandbox.mkdir(parents=True, exist_ok=True)
        (sandbox / "yes.txt").write_text("yes")
        result = await fs.execute_tool(make_call("fs_file_exists", path="yes.txt"))
        data = json.loads(result.content)
        assert data["exists"] is True
        assert data["type"] == "file"

    async def test_exists_false(self, fs: FilesystemMCP) -> None:
        result = await fs.execute_tool(make_call("fs_file_exists", path="no.txt"))
        data = json.loads(result.content)
        assert data["exists"] is False

    async def test_exists_directory(self, fs: FilesystemMCP, sandbox: Path) -> None:
        subdir = sandbox / "subdir"
        subdir.mkdir(parents=True, exist_ok=True)
        result = await fs.execute_tool(make_call("fs_file_exists", path="subdir"))
        data = json.loads(result.content)
        assert data["exists"] is True
        assert data["type"] == "directory"

    async def test_traversal_returns_not_found(self, fs: FilesystemMCP) -> None:
        result = await fs.execute_tool(
            make_call("fs_file_exists", path="../../etc/passwd")
        )
        data = json.loads(result.content)
        assert data["exists"] is False


# ── fs_delete_file ────────────────────────────────────────────────────────────


class TestDeleteFile:
    async def test_delete_existing_file(self, fs: FilesystemMCP, sandbox: Path) -> None:
        sandbox.mkdir(parents=True, exist_ok=True)
        (sandbox / "bye.txt").write_text("delete me")
        result = await fs.execute_tool(make_call("fs_delete_file", path="bye.txt"))
        assert not result.is_error
        data = json.loads(result.content)
        assert data["deleted"] is True
        assert not (sandbox / "bye.txt").exists()

    async def test_delete_missing_returns_error(self, fs: FilesystemMCP) -> None:
        result = await fs.execute_tool(make_call("fs_delete_file", path="ghost.txt"))
        data = json.loads(result.content)
        assert "error" in data

    async def test_delete_directory_returns_error(self, fs: FilesystemMCP, sandbox: Path) -> None:
        subdir = sandbox / "mydir"
        subdir.mkdir(parents=True, exist_ok=True)
        result = await fs.execute_tool(make_call("fs_delete_file", path="mydir"))
        data = json.loads(result.content)
        assert "error" in data
        assert subdir.exists()

    async def test_delete_traversal_blocked(self, fs: FilesystemMCP) -> None:
        result = await fs.execute_tool(
            make_call("fs_delete_file", path="../../important.cfg")
        )
        assert result.is_error


# ── Unknown tool ──────────────────────────────────────────────────────────────


class TestUnknownTool:
    async def test_unknown_tool_returns_error(self, fs: FilesystemMCP) -> None:
        result = await fs.execute_tool(
            ToolCall(id="x", name="fs_explode", arguments={})
        )
        assert result.is_error
        assert "Unknown tool" in result.content


# ── Tool definitions ──────────────────────────────────────────────────────────


class TestToolDefinitions:
    def test_has_five_tools(self, fs: FilesystemMCP) -> None:
        assert len(fs.get_tool_definitions()) == 5

    def test_tool_names(self, fs: FilesystemMCP) -> None:
        names = {td.name for td in fs.get_tool_definitions()}
        assert names == {
            "fs_read_file",
            "fs_write_file",
            "fs_list_directory",
            "fs_file_exists",
            "fs_delete_file",
        }

    def test_server_name(self, fs: FilesystemMCP) -> None:
        assert fs.name == "filesystem"
