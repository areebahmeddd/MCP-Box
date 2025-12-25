import sys
import json
from pathlib import Path

import click

from superbox.cli.utils import config_path
from superbox.shared import s3
from superbox.shared.config import Config, load_env


@click.command()
@click.option("--name", required=True, help="MCP server name to pull")
@click.option(
    "--client",
    required=True,
    type=click.Choice(["vscode", "cursor", "windsurf", "claude", "chatgpt"], case_sensitive=False),
    help="Target client to write config for",
)
def pull(name: str, client: str) -> None:
    """Pull and configure MCP server from registry"""
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

        bucket = cfg.S3_BUCKET_NAME

        click.echo(f"\nFetching server '{name}' from S3 bucket '{bucket}'...")

        servers = s3.list_servers(bucket)

        if name not in servers:
            click.echo(f"Error: Server '{name}' not found in registry")
            click.echo("\nAvailable servers:")
            for server_name in servers.keys():
                click.echo(f"   - {server_name}")
            sys.exit(1)

        target = client.lower()

        path = config_path(target)
        path.parent.mkdir(parents=True, exist_ok=True)

        if path.exists():
            with open(path, "r") as f:
                vscode_config = json.load(f)
        else:
            vscode_config = {}

        display_target = {
            "vscode": "VS Code",
            "cursor": "Cursor",
            "windsurf": "Windsurf",
            "claude": "Claude",
            "chatgpt": "ChatGPT",
        }.get(target, target)

        config_section = "servers" if target == "vscode" else "mcpServers"
        vscode_config.setdefault(config_section, {})

        if name in vscode_config.get(config_section, {}):
            click.echo(f"Warning: Server '{name}' already exists in {display_target} configuration")
            if not click.confirm("Do you want to overwrite it?"):
                click.echo("Aborted")
                sys.exit(0)

        ws_url_with_params = f"{ws_url}?name={name}"
        vscode_config[config_section][name] = {
            "type": "stdio",
            "command": "python",
            "args": ["-m", "superbox.aws.proxy", "--url", ws_url_with_params],
        }

        with open(path, "w") as f:
            json.dump(vscode_config, f, indent=2)

        click.echo("\n" + "=" * 70)
        click.echo("Success!")
        click.echo("=" * 70)
        click.echo(f"\nServer '{name}' added to {display_target} MCP config")
        click.echo(f"WebSocket URL: {ws_url_with_params}")
        click.echo(f"\nLocation: {path}")
    except Exception as e:
        click.echo(f"\nError: {str(e)}")
        sys.exit(1)
