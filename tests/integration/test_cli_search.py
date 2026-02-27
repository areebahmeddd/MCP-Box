from pathlib import Path

import boto3
from click.testing import CliRunner
from moto import mock_aws

from superbox.cli.commands.search import search
from superbox.shared import s3
from tests.conftest import FAKE_ENV, FAKE_ENV_CONTENT

BUCKET = FAKE_ENV["S3_BUCKET_NAME"]


class TestSearchCommand:
    def test_lists_all_servers(self, sample_server: dict) -> None:
        runner = CliRunner()

        with mock_aws():
            boto3.client("s3", region_name="ap-south-1").create_bucket(
                Bucket=BUCKET,
                CreateBucketConfiguration={"LocationConstraint": "ap-south-1"},
            )
            s3.save_server(BUCKET, "weather-mcp", sample_server)
            s3.save_server(
                BUCKET,
                "news-mcp",
                dict(sample_server, name="news-mcp", description="News headlines MCP"),
            )

            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                result = runner.invoke(search)

        assert result.exit_code == 0, result.output
        assert "weather-mcp" in result.output
        assert "news-mcp" in result.output
        assert "2 found" in result.output.lower() or "2" in result.output

    def test_shows_description_and_tools(self, sample_server: dict) -> None:
        runner = CliRunner()

        with mock_aws():
            boto3.client("s3", region_name="ap-south-1").create_bucket(
                Bucket=BUCKET,
                CreateBucketConfiguration={"LocationConstraint": "ap-south-1"},
            )
            s3.save_server(BUCKET, "weather-mcp", sample_server)

            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                result = runner.invoke(search)

        assert "Fetch weather data" in result.output
        assert "github.com" in result.output

    def test_empty_registry_message(self) -> None:
        runner = CliRunner()

        with mock_aws():
            boto3.client("s3", region_name="ap-south-1").create_bucket(
                Bucket=BUCKET,
                CreateBucketConfiguration={"LocationConstraint": "ap-south-1"},
            )

            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                result = runner.invoke(search)

        assert result.exit_code == 0
        assert "no" in result.output.lower() or "found" in result.output.lower()

    def test_missing_env_file_exits(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(search)
        assert result.exit_code != 0
        assert ".env" in result.output
