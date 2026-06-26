import sys
import json
from pathlib import Path
from urllib.parse import quote

import click

from superbox.cli.utils import config_path
from superbox.shared.config import Config, load_env


def get_repo_name(repo_url: str) -> str:
    """Extract repository name from URL."""
    repo_url = repo_url.strip().rstrip("/")

    if repo_url.startswith("git@github.com:"):
        repo_url = repo_url.replace("git@github.com:", "")
    elif "github.com/" in repo_url:
        repo_url = repo_url.split("github.com/")[-1]

    repo_url = repo_url.replace(".git", "")
    parts = repo_url.split("/")

    return parts[-1] if parts else "unknown"


@click.command()
@click.option("--url", required=True, help="Repository URL of the MCP server")
@click.option(
    "--client",
    required=True,
    type=click.Choice(
        ["vscode", "cursor", "antigravity", "claude", "chatgpt"], case_sensitive=False
    ),
    help="Target client to write config for",
)
@click.option("--entrypoint", default="main.py", help="Entrypoint file (default: main.py)")
def test(url: str, client: str, entrypoint: str) -> None:
    """Test MCP server directly from a repository URL without registry registration."""
    try:
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            click.echo("Error: .env file not found in current directory")
            sys.exit(1)

        load_env(env_path)
        cfg = Config()

        worker_url = cfg.CLOUDFLARE_WORKER_URL
        if not worker_url:
            click.echo("Error: CLOUDFLARE_WORKER_URL not found in .env file")
            sys.exit(1)

        worker_url = worker_url.rstrip("/")
        repo_name = get_repo_name(url)

        click.echo("\n" + "=" * 70)
        click.echo("TEST MODE - No Security Checks")
        click.echo("=" * 70)
        click.echo("\nThis server is being tested directly and has NOT gone through:")
        click.echo("  * Security scanning (SonarQube, Bandit, GitGuardian)")
        click.echo("  * Quality checks")
        click.echo("  * Registry validation")
        click.echo("\nNOTE: This server will NOT be available on the platform.")
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
            "antigravity": "Antigravity",
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
        mcp_url = (
            f"{worker_url}/mcp"
            f"?name={test_server_name}"
            f"&test_mode=true"
            f"&repo_url={encoded_url}"
            f"&entrypoint={entrypoint}"
        )

        if target == "vscode":
            entry = {
                "type": "http",
                "url": mcp_url,
            }
        else:
            entry = {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "mcp-remote", mcp_url],
            }

        client_config[config_section][test_server_name] = entry

        with open(path, "w") as f:
            json.dump(client_config, f, indent=2)

        click.echo("\n" + "=" * 70)
        click.echo("Success!")
        click.echo("=" * 70)
        click.echo(f"\nTest server '{test_server_name}' added to {display_target} MCP config")
        click.echo(f"Repository: {url}")
        click.echo(f"Entrypoint: {entrypoint}")
        click.echo(f"Endpoint:   {mcp_url}")
        click.echo(f"\nConfig location: {path}")
        click.echo(
            f"\nRestart {display_target} to use the test server. "
            f"It will appear as '{test_server_name}'."
        )

    except Exception as e:
        click.echo(f"\nError: {str(e)}")
        sys.exit(1)
