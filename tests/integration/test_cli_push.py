import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import boto3
from click.testing import CliRunner
from moto import mock_aws

from superbox.cli.commands.push import push
from superbox.shared import s3
from tests.conftest import FAKE_ENV, FAKE_ENV_CONTENT

BUCKET = FAKE_ENV["S3_BUCKET_NAME"]

SONAR_SUCCESS = {
    "success": True,
    "report_data": {
        "issue_counts": {
            "total": 0,
            "bugs": 0,
            "vulnerabilities": 0,
            "code_smells": 0,
            "security_hotspots": 0,
        },
        "quality_gate": {"status": "OK"},
        "quality_ratings": {"reliability": "A", "security": "A", "maintainability": "A"},
        "metrics": {"coverage": 90.0, "duplicated_lines_density": 0, "ncloc": 100},
        "metadata": {"sonarcloud_url": "https://sonarcloud.io/project"},
    },
}

SNYK_SUCCESS = {
    "success": True,
    "total_vulnerabilities": 0,
    "severity_counts": {},
    "vulnerabilities": [],
}

GG_SUCCESS = {"success": True, "total_secrets": 0, "secrets": []}

BANDIT_SUCCESS = {
    "success": True,
    "total_issues": 0,
    "severity_counts": {},
    "total_lines_scanned": 100,
    "issues": [],
}

TOOL_INFO = {"tool_count": 2, "tool_names": ["get_weather", "get_forecast"]}

SUPERBOX_JSON = {
    "name": "weather-mcp",
    "version": "1.0.0",
    "description": "A weather MCP server",
    "author": "Test Author",
    "lang": "python",
    "license": "MIT",
    "entrypoint": "main.py",
    "repository": {"type": "git", "url": "https://github.com/test/weather-mcp"},
}


def _create_test_bucket() -> None:
    """Create the test bucket within an active mock_aws context."""
    boto3.client("s3", region_name="ap-south-1").create_bucket(
        Bucket=BUCKET,
        CreateBucketConfiguration={"LocationConstraint": "ap-south-1"},
    )


def _mock_auth_check(cfg) -> None:
    """No-op replacement for _check_auth — always passes."""
    pass


def _apply_all_scanner_patches():
    """Return a list of patch context managers for all external scanner calls."""
    return [
        patch("superbox.cli.commands.push._check_auth", side_effect=_mock_auth_check),
        patch("superbox.cli.commands.push.sonarqube.run_analysis", return_value=SONAR_SUCCESS),
        patch("superbox.cli.commands.push.tool_discovery.clone_repo", return_value="/tmp/fake"),
        patch("superbox.cli.commands.push.tool_discovery.discover_tools", return_value=TOOL_INFO),
        patch("superbox.cli.commands.push.snyk.run_scan", return_value=SNYK_SUCCESS),
        patch("superbox.cli.commands.push.ggshield.run_scan", return_value=GG_SUCCESS),
        patch("superbox.cli.commands.push.bandit.run_scan", return_value=BANDIT_SUCCESS),
    ]


class TestPushCommand:
    def test_success_uploads_server_to_s3(self) -> None:
        runner = CliRunner()

        with mock_aws():
            _create_test_bucket()

            with ExitStack() as stack:
                for p in _apply_all_scanner_patches():
                    stack.enter_context(p)
                with runner.isolated_filesystem():
                    Path(".env").write_text(FAKE_ENV_CONTENT)
                    Path("superbox.json").write_text(json.dumps(SUPERBOX_JSON))
                    result = runner.invoke(push)

            assert result.exit_code == 0, result.output
            assert "push complete" in result.output.lower() or "uploading" in result.output.lower()

            stored = s3.get_server(BUCKET, "weather-mcp")
            assert stored is not None
            assert stored["name"] == "weather-mcp"
            assert stored["tools"]["count"] == 2
            assert "get_weather" in stored["tools"]["names"]

    def test_no_superbox_json_and_no_name_flag_exits(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(push)
        assert result.exit_code != 0
        assert "name" in result.output.lower() or "required" in result.output.lower()

    def test_missing_env_exits(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("superbox.json").write_text(json.dumps(SUPERBOX_JSON))
            result = runner.invoke(push)
        assert result.exit_code != 0
        assert ".env" in result.output

    def test_unauthenticated_exits_with_message(self) -> None:
        runner = CliRunner()
        # _check_auth raises SystemExit(1) when not authenticated
        with patch("superbox.cli.commands.push._check_auth", side_effect=SystemExit(1)):
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                Path("superbox.json").write_text(json.dumps(SUPERBOX_JSON))
                result = runner.invoke(push)
        assert result.exit_code != 0

    def test_force_flag_skips_overwrite_prompt(self) -> None:
        runner = CliRunner()

        with mock_aws():
            _create_test_bucket()
            # pre-insert server so "exists" path is taken
            s3.save_server(BUCKET, "weather-mcp", {"name": "weather-mcp"})

            with ExitStack() as stack:
                for p in _apply_all_scanner_patches():
                    stack.enter_context(p)
                with runner.isolated_filesystem():
                    Path(".env").write_text(FAKE_ENV_CONTENT)
                    Path("superbox.json").write_text(json.dumps(SUPERBOX_JSON))
                    result = runner.invoke(push, ["--force"])
            # Should not prompt; should complete
            assert result.exit_code == 0, result.output

    def test_name_flag_overrides_superbox_json(self) -> None:
        runner = CliRunner()
        custom_json = dict(SUPERBOX_JSON, name="json-name")

        with mock_aws():
            _create_test_bucket()

            with ExitStack() as stack:
                for p in _apply_all_scanner_patches():
                    stack.enter_context(p)
                with runner.isolated_filesystem():
                    Path(".env").write_text(FAKE_ENV_CONTENT)
                    Path("superbox.json").write_text(json.dumps(custom_json))
                    result = runner.invoke(push, ["--name", "flag-name"])

            assert result.exit_code == 0, result.output
            # stored under the flag name
            assert s3.get_server(BUCKET, "flag-name") is not None
