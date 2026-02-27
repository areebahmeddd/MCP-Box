from pathlib import Path
from unittest.mock import patch

import boto3
from click.testing import CliRunner
from moto import mock_aws

from superbox.cli.commands.inspect import inspect
from superbox.shared import s3
from tests.conftest import FAKE_ENV, FAKE_ENV_CONTENT

BUCKET = FAKE_ENV["S3_BUCKET_NAME"]


def _create_test_bucket() -> None:
    boto3.client("s3", region_name="ap-south-1").create_bucket(
        Bucket=BUCKET,
        CreateBucketConfiguration={"LocationConstraint": "ap-south-1"},
    )


class TestInspectCommand:
    def test_opens_browser_for_known_server(self, sample_server: dict) -> None:
        runner = CliRunner()

        with mock_aws():
            _create_test_bucket()
            s3.save_server(BUCKET, "weather-mcp", sample_server)

            with (
                patch(
                    "superbox.cli.commands.inspect.webbrowser.open", return_value=True
                ) as mock_open,
                runner.isolated_filesystem(),
            ):
                Path(".env").write_text(FAKE_ENV_CONTENT)
                result = runner.invoke(inspect, ["--name", "weather-mcp"])

        assert result.exit_code == 0, result.output
        mock_open.assert_called_once_with("https://github.com/test/weather-mcp")
        assert "opening repository" in result.output.lower()

    def test_browser_unavailable_prints_url(self, sample_server: dict) -> None:
        """When webbrowser.open returns False the URL is printed as fallback."""
        runner = CliRunner()

        with mock_aws():
            _create_test_bucket()
            s3.save_server(BUCKET, "weather-mcp", sample_server)

            with (
                patch("superbox.cli.commands.inspect.webbrowser.open", return_value=False),
                runner.isolated_filesystem(),
            ):
                Path(".env").write_text(FAKE_ENV_CONTENT)
                result = runner.invoke(inspect, ["--name", "weather-mcp"])

        assert result.exit_code == 0, result.output
        assert "https://github.com/test/weather-mcp" in result.output

    def test_unknown_server_exits_with_error(self, sample_server: dict) -> None:
        runner = CliRunner()

        with mock_aws():
            _create_test_bucket()
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

    def test_server_with_no_repo_url_exits(self) -> None:
        """Server payload missing a repository URL should produce an error."""
        runner = CliRunner()
        server_no_url = {
            "name": "no-url-server",
            "version": "1.0.0",
            "description": "No URL server",
        }

        with mock_aws():
            _create_test_bucket()
            s3.save_server(BUCKET, "no-url-server", server_no_url)

            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                result = runner.invoke(inspect, ["--name", "no-url-server"])

        assert result.exit_code != 0
        assert "url" in result.output.lower() or "repository" in result.output.lower()
