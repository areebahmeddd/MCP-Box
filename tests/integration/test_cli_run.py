from click.testing import CliRunner

from superbox.cli.commands.run import run


class TestRunCommand:
    def test_exits_with_zero(self) -> None:
        """Deprecated command must exit 0 (deprecation warning, not a failure)."""
        runner = CliRunner()
        result = runner.invoke(run, ["--name", "weather-mcp"])
        assert result.exit_code == 0

    def test_prints_deprecation_notice(self) -> None:
        runner = CliRunner()
        result = runner.invoke(run, ["--name", "weather-mcp"])
        assert "deprecated" in result.output.lower()

    def test_suggests_pull_command(self) -> None:
        """Output must direct users to `superbox pull`."""
        runner = CliRunner()
        result = runner.invoke(run, ["--name", "weather-mcp"])
        assert "pull" in result.output.lower()

    def test_includes_server_name_in_suggestion(self) -> None:
        """The suggested pull example should echo back the requested server name."""
        runner = CliRunner()
        result = runner.invoke(run, ["--name", "my-custom-server"])
        assert "my-custom-server" in result.output
