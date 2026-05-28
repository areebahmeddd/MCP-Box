import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from superbox.cli.commands.test import get_repo_name, test
from tests.conftest import FAKE_ENV_CONTENT


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://github.com/acme/my-tool", "my-tool"),
        ("https://github.com/acme/my-tool.git", "my-tool"),
        ("https://github.com/acme/my-tool/", "my-tool"),
        ("git@github.com:acme/my-tool.git", "my-tool"),
        ("git@github.com:acme/my-tool", "my-tool"),
        ("https://github.com/acme/org/deep/my-tool", "my-tool"),
    ],
)
def test_get_repo_name(url: str, expected: str) -> None:
    assert get_repo_name(url) == expected


class TestTestCommand:
    def test_missing_env_file_exits(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(test, ["--url", "https://github.com/a/b", "--client", "vscode"])
        assert result.exit_code != 0
        assert ".env" in result.output

    def test_missing_worker_url_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        runner = CliRunner()
        monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "")
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(test, ["--url", "https://github.com/a/b", "--client", "vscode"])
        assert result.exit_code != 0
        assert "cloudflare_worker_url" in result.output.lower()

    def test_vscode_writes_http_entry_with_test_mode(self, tmp_path: Path) -> None:
        runner = CliRunner()
        config_file = tmp_path / "mcp.json"
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            with patch("superbox.cli.commands.test.config_path", return_value=config_file):
                result = runner.invoke(
                    test, ["--url", "https://github.com/acme/my-tool", "--client", "vscode"]
                )
        assert result.exit_code == 0, result.output
        cfg = json.loads(config_file.read_text())
        entry = cfg["servers"]["my-tool-test"]
        assert entry["type"] == "http"
        assert "test_mode=true" in entry["url"]
        assert "my-tool-test" in entry["url"]

    def test_cursor_writes_stdio_entry(self, tmp_path: Path) -> None:
        runner = CliRunner()
        config_file = tmp_path / "mcp.json"
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            with patch("superbox.cli.commands.test.config_path", return_value=config_file):
                result = runner.invoke(
                    test, ["--url", "https://github.com/acme/my-tool", "--client", "cursor"]
                )
        assert result.exit_code == 0, result.output
        cfg = json.loads(config_file.read_text())
        entry = cfg["mcpServers"]["my-tool-test"]
        assert entry["type"] == "stdio"
        assert "mcp-remote" in entry["args"]

    def test_custom_entrypoint_included_in_url(self, tmp_path: Path) -> None:
        runner = CliRunner()
        config_file = tmp_path / "mcp.json"
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            with patch("superbox.cli.commands.test.config_path", return_value=config_file):
                result = runner.invoke(
                    test,
                    [
                        "--url",
                        "https://github.com/acme/my-tool",
                        "--client",
                        "vscode",
                        "--entrypoint",
                        "server.py",
                    ],
                )
        assert result.exit_code == 0
        cfg = json.loads(config_file.read_text())
        url = cfg["servers"]["my-tool-test"]["url"]
        assert "entrypoint=server.py" in url

    def test_overwrite_prompt_yes_updates_entry(self, tmp_path: Path) -> None:
        runner = CliRunner()
        config_file = tmp_path / "mcp.json"
        config_file.write_text(
            json.dumps({"servers": {"my-tool-test": {"type": "http", "url": "old"}}})
        )
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            with patch("superbox.cli.commands.test.config_path", return_value=config_file):
                result = runner.invoke(
                    test,
                    ["--url", "https://github.com/acme/my-tool", "--client", "vscode"],
                    input="y\n",
                )
        assert result.exit_code == 0
        cfg = json.loads(config_file.read_text())
        assert "test_mode=true" in cfg["servers"]["my-tool-test"]["url"]

    def test_overwrite_prompt_no_aborts_and_preserves_entry(self, tmp_path: Path) -> None:
        runner = CliRunner()
        config_file = tmp_path / "mcp.json"
        config_file.write_text(
            json.dumps({"servers": {"my-tool-test": {"type": "http", "url": "old"}}})
        )
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            with patch("superbox.cli.commands.test.config_path", return_value=config_file):
                result = runner.invoke(
                    test,
                    ["--url", "https://github.com/acme/my-tool", "--client", "vscode"],
                    input="n\n",
                )
        assert result.exit_code == 0
        assert "aborted" in result.output.lower()
        cfg = json.loads(config_file.read_text())
        assert cfg["servers"]["my-tool-test"]["url"] == "old"

    @pytest.mark.parametrize("client", ["antigravity", "claude", "chatgpt"])
    def test_other_clients_write_mcp_servers_section(self, client: str, tmp_path: Path) -> None:
        runner = CliRunner()
        config_file = tmp_path / "mcp.json"
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            with patch("superbox.cli.commands.test.config_path", return_value=config_file):
                result = runner.invoke(
                    test, ["--url", "https://github.com/acme/my-tool", f"--client={client}"]
                )
        assert result.exit_code == 0, result.output
        cfg = json.loads(config_file.read_text())
        entry = cfg["mcpServers"]["my-tool-test"]
        assert entry["type"] == "stdio"

    def test_security_warning_shown_in_output(self, tmp_path: Path) -> None:
        runner = CliRunner()
        config_file = tmp_path / "mcp.json"
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            with patch("superbox.cli.commands.test.config_path", return_value=config_file):
                result = runner.invoke(
                    test, ["--url", "https://github.com/acme/my-tool", "--client", "vscode"]
                )
        assert "TEST MODE" in result.output or "no security checks" in result.output.lower()
