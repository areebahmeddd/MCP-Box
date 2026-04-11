from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from superbox.cli.commands.inspect import inspect
from superbox.shared import s3
from tests.conftest import FAKE_ENV, FAKE_ENV_CONTENT

BUCKET = FAKE_ENV["CLOUDFLARE_R2_BUCKET_NAME"]


class TestInspectCommand:
    def test_opens_browser_for_known_server(self, sample_server: dict, s3_bucket: str) -> None:
        runner = CliRunner()
        s3.save_server(BUCKET, "weather-mcp", sample_server)

        with (
            patch("superbox.cli.commands.inspect.webbrowser.open", return_value=True) as mock_open,
            runner.isolated_filesystem(),
        ):
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(inspect, ["--name", "weather-mcp"])

        assert result.exit_code == 0, result.output
        mock_open.assert_called_once_with("https://github.com/test/weather-mcp")
        assert "opening repository" in result.output.lower()

    def test_browser_unavailable_prints_url_as_fallback(
        self, sample_server: dict, s3_bucket: str
    ) -> None:
        runner = CliRunner()
        s3.save_server(BUCKET, "weather-mcp", sample_server)

        with (
            patch("superbox.cli.commands.inspect.webbrowser.open", return_value=False),
            runner.isolated_filesystem(),
        ):
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(inspect, ["--name", "weather-mcp"])

        assert result.exit_code == 0
        assert "https://github.com/test/weather-mcp" in result.output

    def test_unknown_server_exits_with_not_found_error(
        self, sample_server: dict, s3_bucket: str
    ) -> None:
        runner = CliRunner()
        s3.save_server(BUCKET, "weather-mcp", sample_server)

        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(inspect, ["--name", "ghost-server"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_missing_env_file_exits(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(inspect, ["--name", "weather-mcp"])
        assert result.exit_code != 0
        assert ".env" in result.output

    def test_server_with_no_repository_url_exits_with_error(self, s3_bucket: str) -> None:
        runner = CliRunner()
        s3.save_server(BUCKET, "no-url-server", {"name": "no-url-server", "version": "1.0.0"})

        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(inspect, ["--name", "no-url-server"])

        assert result.exit_code != 0
        assert "url" in result.output.lower() or "repository" in result.output.lower()

    def test_legacy_repo_url_key_accepted(self, s3_bucket: str) -> None:
        runner = CliRunner()
        s3.save_server(
            BUCKET,
            "legacy-server",
            {"name": "legacy-server", "repo_url": "https://github.com/test/legacy"},
        )

        with (
            patch("superbox.cli.commands.inspect.webbrowser.open", return_value=True),
            runner.isolated_filesystem(),
        ):
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(inspect, ["--name", "legacy-server"])

        assert result.exit_code == 0

    def test_exception_in_s3_handled_gracefully(self, s3_bucket: str) -> None:
        runner = CliRunner()
        with (
            patch("superbox.cli.commands.inspect.s3.get_server", side_effect=Exception("R2 down")),
            runner.isolated_filesystem(),
        ):
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(inspect, ["--name", "any"])
        assert result.exit_code != 0
        assert "error" in result.output.lower()
