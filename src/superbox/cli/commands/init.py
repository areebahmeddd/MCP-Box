import sys
import json
import click
from pathlib import Path

from superbox.cli.scanners import sonarqube


AUTH_FILE = Path.home() / ".superbox" / "auth.json"


def _get_logged_in_name() -> str:
    """Return the name (or email) from the local auth file, or empty string if not logged in."""
    if not AUTH_FILE.exists():
        return ""
    try:
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("name") or data.get("email") or ""
    except Exception:
        return ""


@click.command()
def init() -> None:
    """Initialize superbox.json configuration file"""
    config_file = Path.cwd() / "superbox.json"

    if config_file.exists():
        click.echo("superbox.json already exists")
        if not click.confirm("Do you want to overwrite it?"):
            click.echo("Aborted")
            sys.exit(0)

    click.echo("\nInitialize SuperBox Configuration")
    click.echo("=" * 50)

    repo_url = click.prompt("\nRepository URL (GitHub)", default="")
    if repo_url:
        owner, repo = sonarqube.extract_repository(repo_url)
        default_name = repo if repo else ""
    else:
        default_name = Path.cwd().name

    name = click.prompt("Server name", default=default_name)
    version = click.prompt("Version", default="1.0.0")
    description = click.prompt("Description", default=f"MCP server for {name}")
    default_author = _get_logged_in_name()
    author = click.prompt("Author", default=default_author)
    lang = click.prompt(
        "Language",
        default="Python",
        type=click.Choice(["Python", "TypeScript", "JavaScript"], case_sensitive=False),
    )
    license_type = click.prompt("License", default="MIT")

    if lang.lower() == "typescript":
        default_entrypoint = "index.ts"
    elif lang.lower() == "javascript":
        default_entrypoint = "index.js"
    else:
        default_entrypoint = "main.py"

    entrypoint = click.prompt("Entrypoint file", default=default_entrypoint)

    if not repo_url:
        repo_url = click.prompt("Repository URL", default="")

    homepage = click.prompt("Homepage URL (optional)", default="", show_default=False)

    add_pricing = click.confirm("\nAdd pricing information?", default=False)

    config = {
        "name": name,
        "version": version,
        "description": description,
        "author": author,
        "lang": lang,
        "license": license_type,
        "entrypoint": entrypoint,
        "repository": {"type": "git", "url": repo_url},
    }

    if homepage:
        config["homepage"] = homepage

    if add_pricing:
        currency = click.prompt("Currency", default="INR")
        amount = click.prompt("Amount", type=float, default=0.0)
        config["pricing"] = {"currency": currency, "amount": amount}

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    click.echo("\n" + "=" * 50)
    click.echo("Configuration saved!")
    click.echo("=" * 50)
    click.echo(f"\nCreated: {config_file}")
    click.echo("\nNext steps:")
    click.echo(f"   1. superbox push --name {name}")
    click.echo(f"   2. superbox pull --name {name}")
