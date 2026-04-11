from click.testing import CliRunner

from superbox.cli.commands.run import run


class TestRunCommand:
    def test_exits_zero_as_deprecated_command(self) -> None:
        runner = CliRunner()
        result = runner.invoke(run, ["--name", "weather-mcp"])
        assert result.exit_code == 0

    def test_prints_deprecation_notice(self) -> None:
        runner = CliRunner()
        result = runner.invoke(run, ["--name", "weather-mcp"])
        assert "deprecated" in result.output.lower()

    def test_suggests_pull_command(self) -> None:
        runner = CliRunner()
        result = runner.invoke(run, ["--name", "weather-mcp"])
        assert "pull" in result.output.lower()

    def test_includes_requested_server_name_in_suggestion(self) -> None:
        runner = CliRunner()
        result = runner.invoke(run, ["--name", "my-custom-server"])
        assert "my-custom-server" in result.output

    def test_name_option_required(self) -> None:
        runner = CliRunner()
        result = runner.invoke(run, [])
        assert result.exit_code != 0
