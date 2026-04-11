import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from superbox.cli.commands.push import _check_auth, push
from superbox.shared import s3
from superbox.shared.config import Config
from tests.conftest import FAKE_ENV, FAKE_ENV_CONTENT

BUCKET = FAKE_ENV["CLOUDFLARE_R2_BUCKET_NAME"]

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
TOOL_INFO = {"count": 2, "names": ["get_weather", "get_forecast"]}

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


def _scanner_patches():
    return [
        patch("superbox.cli.commands.push._check_auth", side_effect=lambda cfg: None),
        patch("superbox.cli.commands.push.sonarqube.run_analysis", return_value=SONAR_SUCCESS),
        patch("superbox.cli.commands.push.tool_discovery.clone_repo", return_value="/tmp/fake"),
        patch("superbox.cli.commands.push.tool_discovery.discover_tools", return_value=TOOL_INFO),
        patch("superbox.cli.commands.push.snyk.run_scan", return_value=SNYK_SUCCESS),
        patch("superbox.cli.commands.push.ggshield.run_scan", return_value=GG_SUCCESS),
        patch("superbox.cli.commands.push.bandit.run_scan", return_value=BANDIT_SUCCESS),
    ]


class TestPushCommand:
    def test_success_uploads_server_to_registry(self, s3_bucket: str) -> None:
        runner = CliRunner()
        with ExitStack() as stack:
            for p in _scanner_patches():
                stack.enter_context(p)
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                Path("superbox.json").write_text(json.dumps(SUPERBOX_JSON))
                result = runner.invoke(push)

        assert result.exit_code == 0, result.output
        stored = s3.get_server(BUCKET, "weather-mcp")
        assert stored is not None
        assert stored["name"] == "weather-mcp"
        assert stored["tools"]["count"] == 2
        assert "get_weather" in stored["tools"]["names"]

    def test_push_complete_message_shown(self, s3_bucket: str) -> None:
        runner = CliRunner()
        with ExitStack() as stack:
            for p in _scanner_patches():
                stack.enter_context(p)
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                Path("superbox.json").write_text(json.dumps(SUPERBOX_JSON))
                result = runner.invoke(push)
        assert "push complete" in result.output.lower() or "uploading" in result.output.lower()

    def test_no_name_and_no_superbox_json_exits_with_error(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(push)
        assert result.exit_code != 0
        assert "name" in result.output.lower() or "required" in result.output.lower()

    def test_missing_env_file_exits(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("superbox.json").write_text(json.dumps(SUPERBOX_JSON))
            result = runner.invoke(push)
        assert result.exit_code != 0
        assert ".env" in result.output

    def test_unauthenticated_exits_nonzero(self) -> None:
        runner = CliRunner()
        with patch("superbox.cli.commands.push._check_auth", side_effect=SystemExit(1)):
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                Path("superbox.json").write_text(json.dumps(SUPERBOX_JSON))
                result = runner.invoke(push)
        assert result.exit_code != 0

    def test_force_flag_skips_overwrite_prompt(self, s3_bucket: str) -> None:
        runner = CliRunner()
        s3.save_server(BUCKET, "weather-mcp", {"name": "weather-mcp"})
        with ExitStack() as stack:
            for p in _scanner_patches():
                stack.enter_context(p)
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                Path("superbox.json").write_text(json.dumps(SUPERBOX_JSON))
                result = runner.invoke(push, ["--force"])
        assert result.exit_code == 0, result.output

    def test_name_flag_overrides_superbox_json_name(self, s3_bucket: str) -> None:
        runner = CliRunner()
        with ExitStack() as stack:
            for p in _scanner_patches():
                stack.enter_context(p)
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                Path("superbox.json").write_text(json.dumps(SUPERBOX_JSON))
                result = runner.invoke(push, ["--name", "custom-name"])
        assert result.exit_code == 0, result.output
        assert s3.get_server(BUCKET, "custom-name") is not None

    def test_missing_repository_url_exits(self) -> None:
        runner = CliRunner()
        no_repo = {k: v for k, v in SUPERBOX_JSON.items() if k != "repository"}
        with ExitStack() as stack:
            for p in _scanner_patches():
                stack.enter_context(p)
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                Path("superbox.json").write_text(json.dumps(no_repo))
                result = runner.invoke(push)
        assert result.exit_code != 0
        assert "repository" in result.output.lower() or "url" in result.output.lower()

    def test_legacy_repo_url_key_accepted(self, s3_bucket: str) -> None:
        runner = CliRunner()
        legacy = {k: v for k, v in SUPERBOX_JSON.items() if k != "repository"}
        legacy["repo_url"] = "https://github.com/test/weather-mcp"
        with ExitStack() as stack:
            for p in _scanner_patches():
                stack.enter_context(p)
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                Path("superbox.json").write_text(json.dumps(legacy))
                result = runner.invoke(push)
        assert result.exit_code == 0, result.output

    def test_sonar_analysis_failure_exits(self) -> None:
        runner = CliRunner()
        with (
            patch("superbox.cli.commands.push._check_auth", side_effect=lambda cfg: None),
            patch(
                "superbox.cli.commands.push.sonarqube.run_analysis", return_value={"success": False}
            ),
        ):
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                Path("superbox.json").write_text(json.dumps(SUPERBOX_JSON))
                result = runner.invoke(push)
        assert result.exit_code != 0

    def test_homepage_from_config_stored_in_registry(self, s3_bucket: str) -> None:
        runner = CliRunner()
        config_with_homepage = dict(SUPERBOX_JSON, homepage="https://my-mcp.dev")
        with ExitStack() as stack:
            for p in _scanner_patches():
                stack.enter_context(p)
            with runner.isolated_filesystem():
                Path(".env").write_text(FAKE_ENV_CONTENT)
                Path("superbox.json").write_text(json.dumps(config_with_homepage))
                result = runner.invoke(push)
        assert result.exit_code == 0, result.output
        stored = s3.get_server(BUCKET, "weather-mcp")
        assert stored.get("homepage") == "https://my-mcp.dev"


class TestCheckAuth:
    def _cfg(self) -> Config:
        return Config()

    def test_no_auth_file_aborts(self, tmp_path: Path) -> None:
        with patch("superbox.cli.commands.push.AUTH_FILE", tmp_path / "no-auth.json"):
            with pytest.raises(SystemExit):
                _check_auth(self._cfg())

    def test_missing_id_token_aborts(self, tmp_path: Path) -> None:
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps({"email": "u@x.com"}))
        with patch("superbox.cli.commands.push.AUTH_FILE", auth_path):
            with pytest.raises(SystemExit):
                _check_auth(self._cfg())

    def test_invalid_token_lookup_response_aborts(self, tmp_path: Path) -> None:
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps({"id_token": "expired-tok"}))
        bad_resp = MagicMock()
        bad_resp.status_code = 400
        bad_resp.json.return_value = {}
        with (
            patch("superbox.cli.commands.push.AUTH_FILE", auth_path),
            patch("superbox.cli.commands.push.requests.post", return_value=bad_resp),
        ):
            with pytest.raises(SystemExit):
                _check_auth(self._cfg())

    def test_empty_users_list_aborts(self, tmp_path: Path) -> None:
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps({"id_token": "tok"}))
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"users": []}
        with (
            patch("superbox.cli.commands.push.AUTH_FILE", auth_path),
            patch("superbox.cli.commands.push.requests.post", return_value=ok_resp),
        ):
            with pytest.raises(SystemExit):
                _check_auth(self._cfg())

    def test_network_error_aborts(self, tmp_path: Path) -> None:
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps({"id_token": "tok"}))
        with (
            patch("superbox.cli.commands.push.AUTH_FILE", auth_path),
            patch(
                "superbox.cli.commands.push.requests.post", side_effect=Exception("network error")
            ),
        ):
            with pytest.raises(SystemExit):
                _check_auth(self._cfg())

    def test_valid_token_does_not_raise(self, tmp_path: Path) -> None:
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps({"id_token": "valid-tok"}))
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"users": [{"localId": "uid-1"}]}
        with (
            patch("superbox.cli.commands.push.AUTH_FILE", auth_path),
            patch("superbox.cli.commands.push.requests.post", return_value=ok_resp),
        ):
            _check_auth(self._cfg())  # must not raise
