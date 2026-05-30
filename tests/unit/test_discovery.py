import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from superbox.cli.scanners.discovery import (
    check_npm,
    clone_repo,
    discover_tools,
    extract_tools,
    extract_ts,
    scan_package,
    scan_repo,
    scan_typescript,
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


class TestExtractTs:
    @pytest.mark.parametrize(
        "content, expected",
        [
            # SDK v0.x: server.tool(name, description, schema, handler)
            ('server.tool("get_weather", "desc", {}, async () => {})', ["get_weather"]),
            # SDK v1.x: server.registerTool(name, { ... }, handler)
            (
                'server.registerTool("search_nodes", { description: "Search" }, async () => {})',
                ["search_nodes"],
            ),
            # backtick-quoted name
            ("server.tool(`fetch_url`, 'Get URL', {}, async () => {})", ["fetch_url"]),
            # different variable name prefix
            ("mcp.tool('create_entity', 'Create', {}, async () => {})", ["create_entity"]),
        ],
    )
    def test_named_patterns(self, content: str, expected: list[str]) -> None:
        assert sorted(extract_ts(content)) == sorted(expected)

    def test_ignores_private_and_short_names(self) -> None:
        content = 'server.tool("x", "too short", {}, async () => {})'
        assert extract_ts(content) == []

    def test_empty_source_returns_empty(self) -> None:
        assert extract_ts("") == []

    def test_multiple_tools_extracted(self) -> None:
        content = """
server.tool("get_weather", "Get weather", {}, async ({ city }) => {});
server.registerTool("get_forecast", { description: "Forecast" }, async () => {});
"""
        result = extract_ts(content)
        assert "get_weather" in result
        assert "get_forecast" in result

    def test_ignores_sdk_import_lines(self) -> None:
        # import lines should not produce false positives
        content = 'import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";'
        assert extract_ts(content) == []


class TestScanTypeScript:
    def test_finds_tools_in_ts_files(self, tmp_path: Path) -> None:
        (tmp_path / "index.ts").write_text(
            'server.tool("get_data", "Get data", {}, async () => {});\n'
            'server.registerTool("post_data", { description: "Post" }, async () => {});\n'
        )
        result = scan_typescript(str(tmp_path))
        assert result["count"] == 2
        assert "get_data" in result["names"]
        assert "post_data" in result["names"]

    def test_skips_node_modules(self, tmp_path: Path) -> None:
        nm = tmp_path / "node_modules" / "mcp-sdk"
        nm.mkdir(parents=True)
        (nm / "index.ts").write_text(
            'server.tool("sdk_internal", "internal", {}, async () => {});\n'
        )
        result = scan_typescript(str(tmp_path))
        assert "sdk_internal" not in result["names"]

    def test_skips_compiled_dist(self, tmp_path: Path) -> None:
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "index.js").write_text(
            'server.tool("compiled_tool", "compiled", {}, async () => {});\n'
        )
        result = scan_typescript(str(tmp_path))
        assert "compiled_tool" not in result["names"]

    def test_returns_zero_on_empty_directory(self, tmp_path: Path) -> None:
        result = scan_typescript(str(tmp_path))
        assert result == {"count": 0, "names": []}

    def test_names_sorted_alphabetically(self, tmp_path: Path) -> None:
        (tmp_path / "tools.ts").write_text(
            'server.tool("zoo_tool", "Zoo", {}, async () => {});\n'
            'server.tool("alpha_tool", "Alpha", {}, async () => {});\n'
        )
        result = scan_typescript(str(tmp_path))
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


class TestCheckNpm:
    def test_npm_repo_no_python(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "my-mcp"}')
        (tmp_path / "index.ts").write_text("export {};")
        assert check_npm(str(tmp_path)) is True

    def test_python_repo_no_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text("import mcp")
        assert check_npm(str(tmp_path)) is False

    def test_mixed_repo_has_python(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "mixed"}')
        (tmp_path / "helper.py").write_text("# helper")
        assert check_npm(str(tmp_path)) is False

    def test_empty_dir_is_not_npm(self, tmp_path: Path) -> None:
        assert check_npm(str(tmp_path)) is False


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


class TestDiscoverTools:
    def test_merges_python_and_package_json_tools(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text('@mcp.tool("py_tool")\ndef py_tool(): pass\n')
        pkg = {"mcp": {"tools": [{"name": "py_tool"}, {"name": "js_tool"}]}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))
        result = discover_tools(str(tmp_path))
        assert result["names"].count("py_tool") == 1
        assert "js_tool" in result["names"]
        assert result["count"] == 2

    def test_merges_python_and_ts_tools(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text('@mcp.tool("py_tool")\ndef py_tool(): pass\n')
        (tmp_path / "index.ts").write_text('server.tool("ts_tool", "desc", {}, async () => {});\n')
        result = discover_tools(str(tmp_path))
        assert "py_tool" in result["names"]
        assert "ts_tool" in result["names"]

    def test_deduplicates_across_sources(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text('@mcp.tool("shared_tool")\ndef shared_tool(): pass\n')
        (tmp_path / "index.ts").write_text(
            'server.tool("shared_tool", "desc", {}, async () => {});\n'
        )
        result = discover_tools(str(tmp_path))
        assert result["names"].count("shared_tool") == 1

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


class TestDiscoverToolsWithTypeScript:
    def test_merges_python_and_ts_tools(self, tmp_path: Path) -> None:
        (tmp_path / "main.py").write_text('@mcp.tool("py_tool")\ndef py_tool(): pass\n')
        (tmp_path / "index.ts").write_text('server.tool("ts_tool", "desc", {}, async () => {});\n')
        result = discover_tools(str(tmp_path))
        assert "py_tool" in result["names"]
        assert "ts_tool" in result["names"]
        assert result["names"].count("ts_tool") == 1

    def test_deduplicates_across_sources(self, tmp_path: Path) -> None:
        # Same tool name in both Python and TypeScript
        (tmp_path / "main.py").write_text('@mcp.tool("shared_tool")\ndef shared_tool(): pass\n')
        (tmp_path / "index.ts").write_text(
            'server.tool("shared_tool", "desc", {}, async () => {});\n'
        )
        result = discover_tools(str(tmp_path))
        assert result["names"].count("shared_tool") == 1
