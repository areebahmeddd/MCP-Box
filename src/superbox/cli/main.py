import click

from superbox.cli.commands.init import init
from superbox.cli.commands.auth import auth
from superbox.cli.commands.push import push
from superbox.cli.commands.pull import pull
from superbox.cli.commands.run import run
from superbox.cli.commands.search import search
from superbox.cli.commands.inspect import inspect
from superbox.cli.commands.test import test


@click.group()
@click.version_option(version="1.0.0", prog_name="superbox")
def cli():
    """SuperBox CLI"""
    pass


# Register commands
cli.add_command(init)
cli.add_command(auth)
cli.add_command(push)
cli.add_command(pull)
cli.add_command(run)
cli.add_command(search)
cli.add_command(inspect)
cli.add_command(test)


def main():
    """Entry point for CLI"""
    cli()


if __name__ == "__main__":
    main()
