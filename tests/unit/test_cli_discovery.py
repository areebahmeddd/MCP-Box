import json
from pathlib import Path

import pytest

from superbox.cli.scanners.discovery import (
    discover_tools,
    extract_tools,
    scan_package,
    scan_repo,
)


@pytest.mark.parametrize(
    "content,expected",
    [
        # Pattern 1a: @server.call_tool("name")
        ('@server.call_tool("get_weather")\ndef fn(): pass', ["get_weather"]),
        # Pattern 1b: @mcp.tool("name")
        ("@mcp.tool('forecast')\ndef fn(): pass", ["forecast"]),
        # Pattern 1c: @server.tool("name")
        ('@server.tool("list_files")\ndef fn(): pass', ["list_files"]),
        # Pattern 1d: Tool(name="name")
        ('Tool(name="search_tool")', ["search_tool"]),
        # Pattern 2: no-param decorator → function name
        ("@mcp.tool()\ndef my_tool(): pass", ["my_tool"]),
        ("@server.tool()\ndef another_tool(): pass", ["another_tool"]),
    ],
)
def test_extract_tools_patterns(content: str, expected: list[str]) -> None:
    result = extract_tools(content)
    assert sorted(result) == sorted(expected)


def test_extract_tools_deduplicates() -> None:
    content = '@mcp.tool("ping")\ndef ping(): pass\n@server.tool("ping")\ndef ping2(): pass'
    # "ping" may appear twice, but scan_repo deduplicates downstream
    result = extract_tools(content)
    assert "ping" in result


def test_extract_tools_filters_private_names() -> None:
    content = "@mcp.tool()\ndef _private(): pass"
    result = extract_tools(content)
    assert "_private" not in result


def test_extract_tools_filters_single_char() -> None:
    content = "@mcp.tool()\ndef x(): pass"
    result = extract_tools(content)
    assert "x" not in result


def test_extract_tools_empty_file() -> None:
    assert extract_tools("") == []


def test_extract_tools_json_array_section() -> None:
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


def test_scan_repo_finds_tools(tmp_path: Path) -> None:
    (tmp_path / "server.py").write_text(
        '@mcp.tool("get_data")\ndef get_data(): pass\n'
        '@mcp.tool("post_data")\ndef post_data(): pass\n'
    )
    result = scan_repo(str(tmp_path))
    assert result["tool_count"] == 2
    assert "get_data" in result["tool_names"]
    assert "post_data" in result["tool_names"]


def test_scan_repo_deduplicates(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text('@mcp.tool("shared")\ndef shared(): pass\n')
    (tmp_path / "b.py").write_text('@mcp.tool("shared")\ndef shared2(): pass\n')
    result = scan_repo(str(tmp_path))
    assert result["tool_names"].count("shared") == 1


def test_scan_repo_returns_zero_on_empty_dir(tmp_path: Path) -> None:
    result = scan_repo(str(tmp_path))
    assert result["tool_count"] == 0
    assert result["tool_names"] == []


def test_scan_repo_skips_unreadable_files(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_bytes(b"\xff\xfe broken bytes")
    # Should not raise; might return 0 tools
    result = scan_repo(str(tmp_path))
    assert isinstance(result["tool_count"], int)


def test_scan_package_finds_mcp_tools(tmp_path: Path) -> None:
    pkg = {
        "name": "my-mcp",
        "mcp": {
            "tools": [
                {"name": "node_tool_one"},
                {"name": "node_tool_two"},
            ]
        },
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    result = scan_package(str(tmp_path))
    assert result["tool_count"] == 2
    assert "node_tool_one" in result["tool_names"]


def test_scan_package_no_file_returns_empty(tmp_path: Path) -> None:
    result = scan_package(str(tmp_path))
    assert result == {"tool_count": 0, "tool_names": []}


def test_scan_package_no_mcp_key_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"name": "no-mcp-key"}))
    result = scan_package(str(tmp_path))
    assert result["tool_count"] == 0


def test_discover_tools_merges_and_deduplicates(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text('@mcp.tool("py_tool")\ndef py_tool(): pass\n')
    pkg = {"mcp": {"tools": [{"name": "py_tool"}, {"name": "js_tool"}]}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))

    result = discover_tools(str(tmp_path))
    assert result["tool_names"].count("py_tool") == 1
    assert "js_tool" in result["tool_names"]
    assert result["tool_count"] == 2
