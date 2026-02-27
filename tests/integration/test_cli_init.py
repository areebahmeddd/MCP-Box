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
                        "https://github.com/test/my-mcp",  # repo URL
                        "my-mcp",  # name
                        "1.0.0",  # version
                        "A great MCP",  # description
                        "Test Author",  # author
                        "Python",  # lang
                        "MIT",  # license
                        "main.py",  # entrypoint
                        "",  # homepage (skip)
                        "n",  # add pricing? no
                    ]
                ),
            )
            assert result.exit_code == 0
            config = json.loads(Path("superbox.json").read_text())
            assert config["name"] == "my-mcp"
            assert config["version"] == "1.0.0"
            assert config["author"] == "Test Author"
            assert config["repository"]["url"] == "https://github.com/test/my-mcp"

    def test_includes_pricing_when_requested(self) -> None:
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
                        "",  # homepage
                        "y",  # add pricing? yes
                        "INR",
                        "499",
                    ]
                ),
            )
            assert result.exit_code == 0
            config = json.loads(Path("superbox.json").read_text())
            assert config["pricing"]["currency"] == "INR"
            assert float(config["pricing"]["amount"]) == pytest.approx(499.0)

    def test_aborts_if_file_exists_and_user_says_no(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("superbox.json").write_text('{"name": "existing"}')
            result = runner.invoke(init, input="n\n")
            assert result.exit_code == 0
            # file should remain unchanged
            assert json.loads(Path("superbox.json").read_text())["name"] == "existing"

    def test_overwrites_if_user_confirms(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("superbox.json").write_text('{"name": "old"}')
            result = runner.invoke(
                init,
                input="\n".join(
                    [
                        "y",  # overwrite?
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
