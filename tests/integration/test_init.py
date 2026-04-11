import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from superbox.cli.commands.init import init


class TestInitCommand:
    def test_creates_superbox_json_with_user_input(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                init,
                input="\n".join(
                    [
                        "https://github.com/test/my-mcp",
                        "my-mcp",
                        "1.0.0",
                        "A great MCP",
                        "Test Author",
                        "Python",
                        "MIT",
                        "main.py",
                        "",
                        "n",
                    ]
                ),
            )
            assert result.exit_code == 0
            config = json.loads(Path("superbox.json").read_text())
            assert config["name"] == "my-mcp"
            assert config["version"] == "1.0.0"
            assert config["author"] == "Test Author"
            assert config["repository"]["type"] == "git"
            assert config["repository"]["url"] == "https://github.com/test/my-mcp"

    def test_includes_pricing_when_user_opts_in(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                init,
                input="\n".join(
                    [
                        "https://github.com/test/paid-mcp",
                        "paid-mcp",
                        "1.0.0",
                        "A paid MCP",
                        "Author",
                        "Python",
                        "MIT",
                        "main.py",
                        "",
                        "y",
                        "INR",
                        "499",
                    ]
                ),
            )
            assert result.exit_code == 0
            config = json.loads(Path("superbox.json").read_text())
            assert config["pricing"]["currency"] == "INR"
            assert float(config["pricing"]["amount"]) == pytest.approx(499.0)

    def test_aborts_when_file_exists_and_user_declines_overwrite(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("superbox.json").write_text('{"name": "existing"}')
            result = runner.invoke(init, input="n\n")
            assert result.exit_code == 0
            assert json.loads(Path("superbox.json").read_text())["name"] == "existing"

    def test_overwrites_when_user_confirms(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("superbox.json").write_text('{"name": "old"}')
            result = runner.invoke(
                init,
                input="\n".join(
                    [
                        "y",
                        "https://github.com/test/new-mcp",
                        "new-mcp",
                        "2.0.0",
                        "New MCP",
                        "Author",
                        "Python",
                        "MIT",
                        "main.py",
                        "",
                        "n",
                    ]
                ),
            )
            assert result.exit_code == 0
            config = json.loads(Path("superbox.json").read_text())
            assert config["name"] == "new-mcp"
            assert config["version"] == "2.0.0"

    def test_next_steps_shown_in_output(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                init,
                input="\n".join(
                    [
                        "https://github.com/test/my-mcp",
                        "my-mcp",
                        "1.0.0",
                        "desc",
                        "auth",
                        "Python",
                        "MIT",
                        "main.py",
                        "",
                        "n",
                    ]
                ),
            )
            assert "superbox push" in result.output
            assert "superbox pull" in result.output

    def test_homepage_included_when_provided(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                init,
                input="\n".join(
                    [
                        "https://github.com/test/my-mcp",
                        "my-mcp",
                        "1.0.0",
                        "desc",
                        "auth",
                        "Python",
                        "MIT",
                        "main.py",
                        "https://my-mcp.dev",
                        "n",
                    ]
                ),
            )
            assert result.exit_code == 0
            config = json.loads(Path("superbox.json").read_text())
            assert config.get("homepage") == "https://my-mcp.dev"

    def test_no_repo_url_uses_cwd_as_default_name(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                init,
                input="\n".join(
                    [
                        "",
                        "",
                        "1.0.0",
                        "desc",
                        "auth",
                        "Python",
                        "MIT",
                        "main.py",
                        "",
                        "",
                        "n",
                    ]
                ),
            )
            assert result.exit_code == 0
