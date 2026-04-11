import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from superbox.cli.scanners.discovery import (
    clone_repo,
    discover_tools,
    extract_tools,
    scan_package,
    scan_repo,
)


class TestExtractTools:
    @pytest.mark.parametrize(
        "content, expected",
        [
            ('@server.call_tool("get_weather")\ndef fn(): pass', ["get_weather"]),
            ("@mcp.tool('forecast')\ndef fn(): pass", ["forecast"]),
            ('@server.tool("list_files")\ndef fn(): pass', ["list_files"]),
            ('Tool(name="search_tool")', ["search_tool"]),
            ("@mcp.tool()\ndef my_tool(): pass", ["my_tool"]),
            ("@server.tool()\ndef another_tool(): pass", ["another_tool"]),
        ],
    )
    def test_named_patterns(self, content: str, expected: list[str]) -> None:
        assert sorted(extract_tools(content)) == sorted(expected)

    def test_deduplication_not_done_at_this_level(self) -> None:
        content = '@mcp.tool("ping")\ndef ping(): pass\n@server.tool("ping")\ndef ping2(): pass'
        result = extract_tools(content)
        assert "ping" in result

    def test_filters_private_names(self) -> None:
        content = "@mcp.tool()\ndef _private(): pass"
        assert "_private" not in extract_tools(content)

    def test_filters_single_char_names(self) -> None:
        content = "@mcp.tool()\ndef x(): pass"
        assert "x" not in extract_tools(content)

    def test_empty_file_returns_empty_list(self) -> None:
        assert extract_tools("") == []

    def test_json_array_section_extraction(self) -> None:
        content = """
tools_config = {
    "tools": [
        {"name": "alpha_tool", "description": "does alpha"},
        {"name": "beta_tool", "description": "does beta"},
    ]
}
"""
        result = extract_tools(content)
        assert "alpha_tool" in result
        assert "beta_tool" in result

    def test_no_tool_patterns_returns_empty(self) -> None:
        content = "def regular_function():\n    return 42"
        assert extract_tools(content) == []


class TestScanRepo:
    def test_finds_tools_in_python_files(self, tmp_path: Path) -> None:
        (tmp_path / "server.py").write_text(
            '@mcp.tool("get_data")\ndef get_data(): pass\n'
            '@mcp.tool("post_data")\ndef post_data(): pass\n'
        )
        result = scan_repo(str(tmp_path))
        assert result["count"] == 2
        assert "get_data" in result["names"]
        assert "post_data" in result["names"]

    def test_deduplicates_across_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text('@mcp.tool("shared")\ndef shared(): pass\n')
        (tmp_path / "b.py").write_text('@mcp.tool("shared")\ndef shared2(): pass\n')
        result = scan_repo(str(tmp_path))
        assert result["names"].count("shared") == 1

    def test_returns_zero_on_empty_directory(self, tmp_path: Path) -> None:
        result = scan_repo(str(tmp_path))
        assert result["count"] == 0
        assert result["names"] == []

    def test_skips_unreadable_binary_files(self, tmp_path: Path) -> None:
        (tmp_path / "bad.py").write_bytes(b"\xff\xfe broken bytes")
        result = scan_repo(str(tmp_path))
        assert isinstance(result["count"], int)

    def test_names_sorted_alphabetically(self, tmp_path: Path) -> None:
        (tmp_path / "tools.py").write_text(
            '@mcp.tool("zoo_tool")\ndef zoo_tool(): pass\n'
            '@mcp.tool("alpha_tool")\ndef alpha_tool(): pass\n'
        )
        result = scan_repo(str(tmp_path))
        assert result["names"] == sorted(result["names"])


class TestScanPackage:
    def test_finds_mcp_tools_in_package_json(self, tmp_path: Path) -> None:
        pkg = {
            "name": "my-mcp",
            "mcp": {"tools": [{"name": "node_tool_one"}, {"name": "node_tool_two"}]},
        }
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        result = scan_package(str(tmp_path))
        assert result["count"] == 2
        assert "node_tool_one" in result["names"]

    def test_no_file_returns_empty(self, tmp_path: Path) -> None:
        result = scan_package(str(tmp_path))
        assert result == {"count": 0, "names": []}

    def test_no_mcp_key_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"name": "no-mcp-key"}))
        result = scan_package(str(tmp_path))
        assert result["count"] == 0

    def test_mcp_without_tools_key_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text(json.dumps({"mcp": {"description": "no tools"}}))
        result = scan_package(str(tmp_path))
        assert result["count"] == 0

    def test_invalid_json_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text("not valid json {{{")
        result = scan_package(str(tmp_path))
        assert result == {"count": 0, "names": []}

    def test_tools_without_name_field_skipped(self, tmp_path: Path) -> None:
        pkg = {"mcp": {"tools": [{"description": "no name"}, {"name": "valid_tool"}]}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        result = scan_package(str(tmp_path))
        assert result["count"] == 1
        assert "valid_tool" in result["names"]


class TestDiscoverTools:
    def test_merges_python_and_package_json_tools(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text('@mcp.tool("py_tool")\ndef py_tool(): pass\n')
        pkg = {"mcp": {"tools": [{"name": "py_tool"}, {"name": "js_tool"}]}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        result = discover_tools(str(tmp_path))
        assert result["names"].count("py_tool") == 1
        assert "js_tool" in result["names"]
        assert result["count"] == 2

    def test_empty_directory_returns_zero(self, tmp_path: Path) -> None:
        result = discover_tools(str(tmp_path))
        assert result["count"] == 0
        assert result["names"] == []

    def test_result_names_are_sorted(self, tmp_path: Path) -> None:
        (tmp_path / "tools.py").write_text(
            '@mcp.tool("zoo")\ndef zoo(): pass\n@mcp.tool("apple")\ndef apple(): pass\n'
        )
        result = discover_tools(str(tmp_path))
        assert result["names"] == sorted(result["names"])


class TestCloneRepo:
    def test_success_returns_path(self, tmp_path: Path) -> None:
        m = MagicMock()
        m.returncode = 0
        with patch("superbox.cli.scanners.discovery.subprocess.run", return_value=m):
            result = clone_repo("https://github.com/acme/repo", str(tmp_path))
        assert result is not None
        assert "repo" in result

    def test_nonzero_returncode_returns_none(self, tmp_path: Path) -> None:
        m = MagicMock()
        m.returncode = 1
        m.stderr = "Repository not found"
        with patch("superbox.cli.scanners.discovery.subprocess.run", return_value=m):
            result = clone_repo("https://github.com/acme/repo", str(tmp_path))
        assert result is None

    def test_timeout_exception_returns_none(self, tmp_path: Path) -> None:
        with patch(
            "superbox.cli.scanners.discovery.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=180),
        ):
            result = clone_repo("https://github.com/acme/repo", str(tmp_path))
        assert result is None

    def test_generic_exception_returns_none(self, tmp_path: Path) -> None:
        with patch(
            "superbox.cli.scanners.discovery.subprocess.run",
            side_effect=OSError("git not found"),
        ):
            result = clone_repo("https://github.com/acme/repo", str(tmp_path))
        assert result is None
