import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from superbox.cli.commands.pull import pull
from superbox.shared import s3
from tests.conftest import FAKE_ENV, FAKE_ENV_CONTENT

BUCKET = FAKE_ENV["CLOUDFLARE_R2_BUCKET_NAME"]


class TestPullCommand:
    def test_cursor_writes_mcp_remote_stdio_config(
        self, tmp_path: Path, sample_server: dict, s3_bucket: str
    ) -> None:
        runner = CliRunner()
        mcp_config = tmp_path / "mcp.json"
        s3.save_server(BUCKET, "weather-mcp", sample_server)

        with patch("superbox.cli.commands.pull.config_path", return_value=mcp_config):
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                result = runner.invoke(pull, ["--name", "weather-mcp", "--client", "cursor"])

        assert result.exit_code == 0, result.output
        written = json.loads(mcp_config.read_text())
        entry = written["mcpServers"]["weather-mcp"]
        assert entry["command"] == "npx"
        assert "mcp-remote" in entry["args"]
        assert any("weather-mcp" in str(a) for a in entry["args"])

    def test_vscode_writes_http_transport_config(
        self, tmp_path: Path, sample_server: dict, s3_bucket: str
    ) -> None:
        runner = CliRunner()
        mcp_config = tmp_path / "mcp.json"
        s3.save_server(BUCKET, "weather-mcp", sample_server)

        with patch("superbox.cli.commands.pull.config_path", return_value=mcp_config):
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                result = runner.invoke(pull, ["--name", "weather-mcp", "--client", "vscode"])

        assert result.exit_code == 0
        written = json.loads(mcp_config.read_text())
        entry = written["servers"]["weather-mcp"]
        assert entry["type"] == "http"
        assert "weather-mcp" in entry["url"]

    @pytest.mark.parametrize("client", ["windsurf", "claude", "chatgpt"])
    def test_other_clients_write_mcp_remote_stdio_config(
        self, client: str, tmp_path: Path, sample_server: dict, s3_bucket: str
    ) -> None:
        runner = CliRunner()
        mcp_config = tmp_path / "mcp.json"
        s3.save_server(BUCKET, "weather-mcp", sample_server)

        with patch("superbox.cli.commands.pull.config_path", return_value=mcp_config):
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                result = runner.invoke(pull, ["--name", "weather-mcp", f"--client={client}"])

        assert result.exit_code == 0, result.output
        written = json.loads(mcp_config.read_text())
        entry = written["mcpServers"]["weather-mcp"]
        assert entry["type"] == "stdio"

    def test_server_not_found_shows_available_list(
        self, tmp_path: Path, sample_server: dict, s3_bucket: str
    ) -> None:
        runner = CliRunner()
        mcp_config = tmp_path / "mcp.json"
        s3.save_server(BUCKET, "weather-mcp", sample_server)

        with patch("superbox.cli.commands.pull.config_path", return_value=mcp_config):
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                result = runner.invoke(pull, ["--name", "no-such-server", "--client", "cursor"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()
        assert "weather-mcp" in result.output

    def test_missing_env_file_exits_with_error(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(pull, ["--name", "x", "--client", "cursor"])
        assert result.exit_code != 0
        assert ".env" in result.output

    def test_overwrite_prompt_abort_preserves_existing_config(
        self, tmp_path: Path, sample_server: dict, s3_bucket: str
    ) -> None:
        runner = CliRunner()
        mcp_config = tmp_path / "mcp.json"
        mcp_config.write_text(json.dumps({"mcpServers": {"weather-mcp": {"existing": True}}}))
        s3.save_server(BUCKET, "weather-mcp", sample_server)

        with patch("superbox.cli.commands.pull.config_path", return_value=mcp_config):
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                runner.invoke(pull, ["--name", "weather-mcp", "--client", "cursor"], input="n\n")

        written = json.loads(mcp_config.read_text())
        assert written["mcpServers"]["weather-mcp"].get("existing") is True

    def test_missing_worker_url_exits_with_error(self, monkeypatch) -> None:
        runner = CliRunner()
        monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "")
        with runner.isolated_filesystem():
            Path(".env").write_text("CLOUDFLARE_WORKER_URL=\n")
            result = runner.invoke(pull, ["--name", "x", "--client", "cursor"])
        assert result.exit_code != 0
        assert "cloudflare_worker_url" in result.output.lower()

    def test_success_message_shown(
        self, tmp_path: Path, sample_server: dict, s3_bucket: str
    ) -> None:
        runner = CliRunner()
        mcp_config = tmp_path / "mcp.json"
        s3.save_server(BUCKET, "weather-mcp", sample_server)

        with patch("superbox.cli.commands.pull.config_path", return_value=mcp_config):
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                result = runner.invoke(pull, ["--name", "weather-mcp", "--client", "cursor"])

        assert "success" in result.output.lower()

    def test_exception_in_s3_handled_gracefully(self) -> None:
        runner = CliRunner()
        with (
            patch("superbox.cli.commands.pull.s3.list_servers", side_effect=Exception("R2 down")),
            runner.isolated_filesystem(),
        ):
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(pull, ["--name", "x", "--client", "cursor"])
        assert result.exit_code != 0
        assert "error" in result.output.lower()
