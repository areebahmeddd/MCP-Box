import json
from pathlib import Path
from unittest.mock import patch

import boto3
from click.testing import CliRunner
from moto import mock_aws

from superbox.cli.commands.pull import pull
from superbox.shared import s3
from tests.conftest import FAKE_ENV, FAKE_ENV_CONTENT

BUCKET = FAKE_ENV["S3_BUCKET_NAME"]


def _setup_bucket_with_server(sample_server: dict) -> None:
    """Create the bucket and insert the sample server (within active mock_aws context)."""
    boto3.client("s3", region_name="ap-south-1").create_bucket(
        Bucket=BUCKET,
        CreateBucketConfiguration={"LocationConstraint": "ap-south-1"},
    )
    s3.save_server(BUCKET, "weather-mcp", sample_server)


class TestPullCommand:
    def test_success_writes_correct_config(self, tmp_path: Path, sample_server: dict) -> None:
        runner = CliRunner()
        mcp_config = tmp_path / "mcp.json"

        with mock_aws():
            _setup_bucket_with_server(sample_server)
            with patch("superbox.cli.commands.pull.config_path", return_value=mcp_config):
                with runner.isolated_filesystem():
                    Path(".env").write_text(FAKE_ENV_CONTENT)
                    result = runner.invoke(pull, ["--name", "weather-mcp", "--client", "cursor"])

        assert result.exit_code == 0, result.output
        assert "success" in result.output.lower()

        written = json.loads(mcp_config.read_text())
        entry = written["mcpServers"]["weather-mcp"]
        assert entry["type"] == "stdio"
        assert "-m" in entry["args"]
        assert "superbox.aws.proxy" in entry["args"]
        assert any("weather-mcp" in str(a) for a in entry["args"])

    def test_adds_vscode_under_servers_key(self, tmp_path: Path, sample_server: dict) -> None:
        runner = CliRunner()
        mcp_config = tmp_path / "mcp.json"

        with mock_aws():
            _setup_bucket_with_server(sample_server)
            with patch("superbox.cli.commands.pull.config_path", return_value=mcp_config):
                with runner.isolated_filesystem():
                    Path(".env").write_text(FAKE_ENV_CONTENT)
                    result = runner.invoke(pull, ["--name", "weather-mcp", "--client", "vscode"])

        assert result.exit_code == 0
        written = json.loads(mcp_config.read_text())
        # VS Code uses "servers", not "mcpServers"
        assert "weather-mcp" in written.get("servers", {})

    def test_server_not_found_shows_available(self, tmp_path: Path, sample_server: dict) -> None:
        runner = CliRunner()
        mcp_config = tmp_path / "mcp.json"

        with mock_aws():
            _setup_bucket_with_server(sample_server)
            with patch("superbox.cli.commands.pull.config_path", return_value=mcp_config):
                with runner.isolated_filesystem():
                    Path(".env").write_text(FAKE_ENV_CONTENT)
                    result = runner.invoke(pull, ["--name", "no-such-server", "--client", "cursor"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()
        assert "weather-mcp" in result.output  # lists available

    def test_missing_env_file_exits_with_error(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(pull, ["--name", "x", "--client", "cursor"])
        assert result.exit_code != 0
        assert ".env" in result.output

    def test_overwrite_prompt_abort(self, tmp_path: Path, sample_server: dict) -> None:
        runner = CliRunner()
        mcp_config = tmp_path / "mcp.json"
        # pre-populate the config with the same server name
        mcp_config.write_text(json.dumps({"mcpServers": {"weather-mcp": {"existing": True}}}))

        with mock_aws():
            _setup_bucket_with_server(sample_server)
            with patch("superbox.cli.commands.pull.config_path", return_value=mcp_config):
                with runner.isolated_filesystem():
                    Path(".env").write_text(FAKE_ENV_CONTENT)
                    result = runner.invoke(
                        pull,
                        ["--name", "weather-mcp", "--client", "cursor"],
                        input="n\n",
                    )

        assert result.exit_code == 0
        # original entry should be intact
        written = json.loads(mcp_config.read_text())
        assert written["mcpServers"]["weather-mcp"].get("existing") is True
