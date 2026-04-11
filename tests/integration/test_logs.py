from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from superbox.cli.commands.logs import logs
from tests.conftest import FAKE_ENV_CONTENT

_SERVER = {"name": "my-mcp", "description": "A test server"}


class TestLogsCommand:
    def test_missing_env_file_exits(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(logs, ["--name", "my-mcp"])
        assert result.exit_code != 0
        assert ".env" in result.output

    def test_server_not_found_exits_with_hint(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            with patch("superbox.cli.commands.logs.s3.get_server", return_value=None):
                result = runner.invoke(logs, ["--name", "missing-server"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()
        assert "superbox search" in result.output

    def test_shows_wrangler_and_cloudflare_instructions(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            with patch("superbox.cli.commands.logs.s3.get_server", return_value=_SERVER):
                result = runner.invoke(logs, ["--name", "my-mcp"])
        assert result.exit_code == 0
        assert "wrangler" in result.output.lower()
        assert "cloudflare" in result.output.lower()

    def test_follow_flag_shows_tail_command_with_server_name(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            with patch("superbox.cli.commands.logs.s3.get_server", return_value=_SERVER):
                result = runner.invoke(logs, ["--name", "my-mcp", "--follow"])
        assert result.exit_code == 0
        assert "wrangler tail" in result.output
        assert "my-mcp" in result.output

    def test_server_description_shown_in_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            with patch("superbox.cli.commands.logs.s3.get_server", return_value=_SERVER):
                result = runner.invoke(logs, ["--name", "my-mcp"])
        assert "A test server" in result.output

    def test_exception_handled_gracefully(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            with patch(
                "superbox.cli.commands.logs.s3.get_server", side_effect=Exception("R2 down")
            ):
                result = runner.invoke(logs, ["--name", "my-mcp"])
        assert result.exit_code != 0
        assert "error" in result.output.lower()
