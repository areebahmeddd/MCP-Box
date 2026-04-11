from pathlib import Path

from click.testing import CliRunner

from superbox.cli.commands.search import search
from superbox.shared import s3
from tests.conftest import FAKE_ENV, FAKE_ENV_CONTENT

BUCKET = FAKE_ENV["CLOUDFLARE_R2_BUCKET_NAME"]


class TestSearchCommand:
    def test_lists_all_servers_with_count(self, sample_server: dict, s3_bucket: str) -> None:
        runner = CliRunner()
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
        assert "2" in result.output

    def test_shows_description_and_repo(self, sample_server: dict, s3_bucket: str) -> None:
        runner = CliRunner()
        s3.save_server(BUCKET, "weather-mcp", sample_server)

        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(search)

        assert "Fetch weather data" in result.output
        assert "github.com" in result.output

    def test_shows_tool_count(self, s3_bucket: str) -> None:
        runner = CliRunner()
        server = {
            "name": "tool-rich",
            "description": "Many tools",
            "repository": {"url": "https://github.com/a/b"},
            "tools": {"count": 5, "names": ["t1", "t2", "t3", "t4", "t5"]},
        }
        s3.save_server(BUCKET, "tool-rich", server)

        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(search)

        assert "5" in result.output

    def test_empty_registry_shows_no_servers_message(self, s3_bucket: str) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(search)
        assert result.exit_code == 0
        assert "no" in result.output.lower() or "found" in result.output.lower()

    def test_missing_env_file_exits_with_error(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(search)
        assert result.exit_code != 0
        assert ".env" in result.output

    def test_shows_security_passed_when_zero_issues(self, s3_bucket: str) -> None:
        runner = CliRunner()
        server = {
            "name": "secure-mcp",
            "description": "Secure server",
            "repository": {"url": "https://github.com/a/b"},
            "tools": {"count": 1, "names": ["ping"]},
            "security_report": {"summary": {"total_issues_all_scanners": 0}},
        }
        s3.save_server(BUCKET, "secure-mcp", server)

        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(search)

        assert "passed" in result.output.lower()

    def test_shows_issue_count_when_security_issues_exist(self, s3_bucket: str) -> None:
        runner = CliRunner()
        server = {
            "name": "risky-mcp",
            "description": "Risky server",
            "repository": {"url": "https://github.com/a/b"},
            "tools": {"count": 1, "names": ["exec"]},
            "security_report": {"summary": {"total_issues_all_scanners": 3}},
        }
        s3.save_server(BUCKET, "risky-mcp", server)

        with runner.isolated_filesystem():
            Path(".env").write_text(FAKE_ENV_CONTENT)
            result = runner.invoke(search)

        assert "3" in result.output
