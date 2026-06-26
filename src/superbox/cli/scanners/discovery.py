import re
import json
import subprocess
from pathlib import Path
from typing import Any


def extract_tools(content: str) -> list[str]:
    """Extract MCP tool names from Python source."""
    tools = []

    # Pattern 1: Decorators with explicit names
    tool_patterns = [
        r'@server\.call_tool\(["\']([^"\']+)["\']\)',
        r'@mcp\.tool\(["\']([^"\']+)["\']\)',
        r'@server\.tool\(["\']([^"\']+)["\']\)',
        r'Tool\(name=["\']([^"\']+)["\']\)',
        r'name=["\']([^"\']+)["\'].*type=["\']tool["\']',
    ]

    for pattern in tool_patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        tools.extend(matches)

    # Pattern 2: Decorator without params - extract function name
    decorator_function_pattern = r"@(?:mcp|server)\.tool\(\s*\)\s*\ndef\s+(\w+)"
    decorator_matches = re.findall(decorator_function_pattern, content, re.MULTILINE | re.DOTALL)
    tools.extend(decorator_matches)

    if '"tools"' in content or "'tools'" in content:
        try:
            tools_section = re.search(r'["\']tools["\']\s*:\s*\[(.*?)\]', content, re.DOTALL)
            if tools_section:
                tool_names = re.findall(
                    r'["\']name["\']\s*:\s*["\']([^"\']+)["\']', tools_section.group(1)
                )
                tools.extend(tool_names)
        except Exception:
            pass

    tools = [t for t in tools if t and not t.startswith("_") and len(t) > 1]

    return tools


def scan_repo(repo_path: str) -> dict[str, Any]:
    """Discover MCP tools from Python files in a repository."""
    tools = []

    python_files = list(Path(repo_path).rglob("*.py"))

    for py_file in python_files:
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            file_tools = extract_tools(content)
            tools.extend(file_tools)
        except Exception:
            continue

    unique_tools = list(set(tools))

    return {"count": len(unique_tools), "names": sorted(unique_tools)}


def extract_ts(content: str) -> list[str]:
    """Extract MCP tool names from TypeScript/JavaScript source."""
    tools = []

    # Pattern: .tool("name", ...) or .registerTool("name", ...)
    tool_patterns = [
        r'\.(?:registerTool|tool)\(\s*["\'`]([A-Za-z_][\w]*)["\' `]',
    ]

    for pattern in tool_patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        tools.extend(matches)

    tools = [t for t in tools if t and not t.startswith("_") and len(t) > 1]

    return tools


def scan_typescript(repo_path: str) -> dict[str, Any]:
    """Discover MCP tools from TypeScript and JavaScript files in a repository."""
    tools = []

    ts_files = list(Path(repo_path).rglob("*.ts")) + list(Path(repo_path).rglob("*.js"))
    # skip dist/, node_modules/, and .d.ts files
    ts_files = [
        f
        for f in ts_files
        if "node_modules" not in f.parts and "dist" not in f.parts and ".d.ts" not in f.name
    ]

    for ts_file in ts_files:
        try:
            with open(ts_file, "r", encoding="utf-8") as f:
                content = f.read()

            file_tools = extract_ts(content)
            tools.extend(file_tools)
        except Exception:
            continue

    unique_tools = list(set(tools))

    return {"count": len(unique_tools), "names": sorted(unique_tools)}


def scan_package(repo_path: str) -> dict[str, Any]:
    """Discover MCP tools declared in package.json under the mcp.tools key."""
    package_json = Path(repo_path) / "package.json"

    if not package_json.exists():
        return {"count": 0, "names": []}

    try:
        with open(package_json, "r") as f:
            data = json.load(f)

        tools = []

        if "mcp" in data and "tools" in data["mcp"]:
            tools = [tool.get("name") for tool in data["mcp"]["tools"] if "name" in tool]

        return {"count": len(tools), "names": sorted(tools)}
    except Exception:
        return {"count": 0, "names": []}


def clone_repo(repo_url: str, target_dir: str) -> str | None:
    """Clone a repository to target_dir and return the clone path, or None on failure."""
    try:
        repo_path = Path(target_dir) / "repo"
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            return None
        return str(repo_path)
    except Exception:
        return None


def check_npm(repo_path: str) -> bool:
    """Return True if the repository uses npm (has package.json and no Python files)."""
    path = Path(repo_path)
    has_package_json = (path / "package.json").exists()
    python_files = [f for f in path.rglob("*.py") if "node_modules" not in f.parts]
    return has_package_json and len(python_files) == 0


def discover_tools(repo_path: str) -> dict[str, Any]:
    """Discover tools from source files and package.json, deduplicated."""
    from_repo = scan_repo(repo_path)
    from_ts = scan_typescript(repo_path)
    from_pkg = scan_package(repo_path)
    names = sorted(
        list(set(from_repo.get("names", []) + from_ts.get("names", []) + from_pkg.get("names", [])))
    )
    return {"count": len(names), "names": names}
