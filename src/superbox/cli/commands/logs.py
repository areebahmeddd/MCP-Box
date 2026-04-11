import sys
from pathlib import Path

import click

from superbox.shared import s3
from superbox.shared.config import Config, load_env


@click.command()
@click.option("--name", required=True, help="MCP server name to fetch logs for")
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Show real-time tail instructions",
)
def logs(name: str, follow: bool) -> None:
    """View execution logs for an MCP server (via Cloudflare Workers)."""
    try:
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            click.echo("Error: .env file not found in current directory")
            sys.exit(1)

        load_env(env_path)
        cfg = Config()

        bucket = cfg.CLOUDFLARE_R2_BUCKET_NAME

        click.echo(f"\nFetching server '{name}' from registry...")
        server = s3.get_server(bucket, name)
        if not server:
            click.echo(f"Error: Server '{name}' not found in registry")
            click.echo("\nTip: Use 'superbox search' to see available servers")
            sys.exit(1)

        click.echo(f"Server found: {server.get('description', 'No description')}")

        click.echo("\n" + "=" * 70)
        click.echo("Cloudflare Workers Logs")
        click.echo("=" * 70)
        click.echo("\nLogs are streamed via the Wrangler CLI or Cloudflare Dashboard.\n")

        if follow:
            click.echo("To tail logs in real-time, run:\n")
            click.echo("  wrangler tail superbox-executor --format pretty\n")
            click.echo(
                f"This streams all Worker invocations including session activity for '{name}'."
            )
        else:
            click.echo("To view recent logs:")
            click.echo()
            click.echo("  Option 1 - Wrangler CLI (real-time):")
            click.echo("    wrangler tail superbox-executor --format pretty")
            click.echo()
            click.echo("  Option 2 - Cloudflare Dashboard:")
            click.echo("    https://dash.cloudflare.com -> Workers & Pages")
            click.echo("    -> superbox-executor -> Logs")
            click.echo()
            click.echo(
                f"Filter by server name in the log stream to see only activity for '{name}'."
            )

        click.echo("=" * 70)

    except Exception as e:
        click.echo(f"\nError: {str(e)}")
        sys.exit(1)
