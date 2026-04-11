import sys
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from superbox.cli.main import cli, display_banner, main


EXPECTED_COMMANDS = {"init", "auth", "push", "pull", "run", "search", "inspect", "test", "logs"}


class TestCliGroup:
    def test_all_expected_commands_registered(self) -> None:
        assert set(cli.commands.keys()) >= EXPECTED_COMMANDS

    def test_help_exits_zero(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_version_option_shows_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_unknown_command_exits_nonzero(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["nonexistent-command"])
        assert result.exit_code != 0

    def test_no_args_shows_help_or_exits_cleanly(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, [])
        assert result.exit_code == 0


class TestDisplayBanner:
    def test_returns_early_for_help_flag(self) -> None:
        with patch.object(sys, "argv", ["superbox", "--help"]):
            display_banner()

    def test_returns_early_for_version_flag(self) -> None:
        with patch.object(sys, "argv", ["superbox", "--version"]):
            display_banner()

    def test_missing_banner_file_does_not_raise(self) -> None:
        with patch.object(sys, "argv", ["superbox", "search"]):
            display_banner()

    def test_banner_content_printed_when_file_exists(self, tmp_path: Path, capsys) -> None:
        banner_file = tmp_path / "banner.txt"
        banner_file.write_text("SuperBox Banner!")
        real_path_class = Path

        def patched_path(*args, **kwargs):
            p = real_path_class(*args, **kwargs)
            if args and args[0] == __file__:
                return banner_file.parent
            return p

        with (
            patch.object(sys, "argv", ["superbox", "search"]),
            patch("superbox.cli.main.Path") as mock_cls,
        ):
            instance = mock_cls.return_value
            instance.__truediv__ = lambda self, other: banner_file
            instance.parent = banner_file.parent
            display_banner()
        out = capsys.readouterr().out
        assert "SuperBox Banner!" in out


class TestMain:
    def test_main_is_callable(self) -> None:
        with (
            patch("superbox.cli.main.display_banner"),
            patch("superbox.cli.main.cli"),
        ):
            main()

    def test_main_calls_display_banner_and_cli(self) -> None:
        with (
            patch("superbox.cli.main.display_banner") as mock_banner,
            patch("superbox.cli.main.cli") as mock_cli,
        ):
            main()
        mock_banner.assert_called_once()
        mock_cli.assert_called_once()
