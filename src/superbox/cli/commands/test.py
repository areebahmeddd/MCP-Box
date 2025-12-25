import sys
import json
from pathlib import Path
from urllib.parse import quote

import click

from superbox.cli.utils import config_path
from superbox.shared.config import Config, load_env


def get_repo(repo_url: str) -> str:
    """Extract repository name from URL"""
    repo_url = repo_url.strip().rstrip("/")

    if repo_url.startswith("git@github.com:"):
        repo_url = repo_url.replace("git@github.com:", "")
    elif "github.com/" in repo_url:
        repo_url = repo_url.split("github.com/")[-1]

    repo_url = repo_url.replace(".git", "")
    parts = repo_url.split("/")

    if len(parts) >= 2:
        return parts[-1]
    return parts[-1] if parts else "unknown"


@click.command()
@click.option("--url", required=True, help="Repository URL of the MCP server")
@click.option(
    "--client",
    required=True,
    type=click.Choice(["vscode", "cursor", "windsurf", "claude", "chatgpt"], case_sensitive=False),
    help="Target client to write config for",
)
@click.option("--entrypoint", default="main.py", help="Entrypoint file (default: main.py)")
@click.option("--lang", default="python", help="Language (default: python)")
def test(url: str, client: str, entrypoint: str, lang: str) -> None:
    """Test MCP server directly from repository URL without S3 registration."""
    try:
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            click.echo("Error: .env file not found in current directory")
            sys.exit(1)

        load_env(env_path)
        cfg = Config()

        ws_url = cfg.WEBSOCKET_URL
        if not ws_url:
            click.echo("Error: WEBSOCKET_URL not found in .env file")
            sys.exit(1)

        repo_name = get_repo(url)

        click.echo("\n" + "=" * 70)
        click.echo("⚠️  TEST MODE - No Security Checks")
        click.echo("=" * 70)
        click.echo("\nThis server is being tested directly and has NOT gone through:")
        click.echo("  • Security scanning (SonarQube, Bandit, GitGuardian)")
        click.echo("  • Quality checks")
        click.echo("  • Registry validation")
        click.echo("\n⚠️  This server will NOT be available on the platform.")
        click.echo("=" * 70 + "\n")

        target = client.lower()
        path = config_path(target)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            with open(path, "r") as f:
                client_config = json.load(f)
        else:
            client_config = {}

        display_target = {
            "vscode": "VS Code",
            "cursor": "Cursor",
            "windsurf": "Windsurf",
            "claude": "Claude",
            "chatgpt": "ChatGPT",
        }.get(target, target)

        config_section = "servers" if target == "vscode" else "mcpServers"
        client_config.setdefault(config_section, {})

        test_server_name = f"{repo_name}-test"

        if test_server_name in client_config.get(config_section, {}):
            click.echo(
                f"Warning: Server '{test_server_name}' already exists in {display_target} configuration"
            )
            if not click.confirm("Do you want to overwrite it?"):
                click.echo("Aborted")
                sys.exit(0)

        encoded_url = quote(url, safe="")
        ws_url_with_params = (
            f"{ws_url}?test_mode=true&repo_url={encoded_url}&entrypoint={entrypoint}&lang={lang}"
        )

        client_config[config_section][test_server_name] = {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "superbox.aws.proxy", "--url", ws_url_with_params],
        }

        with open(path, "w") as f:
            json.dump(client_config, f, indent=2)

        click.echo("\n" + "=" * 70)
        click.echo("Success!")
        click.echo("=" * 70)
        click.echo(f"\nTest server '{test_server_name}' added to {display_target} MCP config")
        click.echo(f"Repository: {url}")
        click.echo(f"Entrypoint: {entrypoint}")
        click.echo(f"Language: {lang}")
        click.echo(f"\nConfig location: {path}")
        click.echo(
            f"\nRestart {display_target} to use the test server. It will appear as '{test_server_name}'."
        )

    except Exception as e:
        click.echo(f"\nError: {str(e)}")
        sys.exit(1)
