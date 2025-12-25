import sys

import click


@click.command()
@click.option("--name", required=True, help="MCP server name to run")
def run(name: str) -> None:
    """Start an interactive session posting prompts to the MCP executor."""
    click.echo("\n⚠️  The 'run' command is deprecated.")
    click.echo("\nPlease use 'superbox pull' to configure the server in VS Code,")
    click.echo("then interact with it through the MCP panel or GitHub Copilot.")
    click.echo("\nExample:")
    click.echo(f"  superbox pull --name {name} --client vscode")
    sys.exit(0)
