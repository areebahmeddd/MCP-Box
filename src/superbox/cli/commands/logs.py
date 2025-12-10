import sys
from pathlib import Path
from datetime import datetime, timedelta

import click
import boto3

from superbox.shared import s3
from superbox.shared.config import Config, load_env


@click.command()
@click.option("--name", required=True, help="MCP server name to fetch logs for")
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow log output in real-time",
)
def logs(name: str, follow: bool) -> None:
    try:
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            click.echo("Error: .env file not found in current directory")
            sys.exit(1)

        load_env(env_path)
        cfg = Config()

        bucket = cfg.S3_BUCKET_NAME

        click.echo(f"\nFetching server '{name}' from registry...")
        server = s3.get_server(bucket, name)
        if not server:
            click.echo(f"Error: Server '{name}' not found in registry")
            click.echo("\nTip: Use 'superbox search' to see available servers")
            sys.exit(1)

        click.echo(f"Server found: {server.get('description', 'No description')}")

        log_group_name = f"/aws/lambda/superbox-executor-{name}"

        logs_client = boto3.client(
            "logs",
            region_name=cfg.AWS_REGION,
            aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
        )

        try:
            response = logs_client.describe_log_groups(logGroupNamePrefix=log_group_name, limit=1)
            if not response.get("logGroups"):
                raise Exception("Log group not found")
        except Exception:
            click.echo(
                f"\nWarning: Unable to access CloudWatch logs for '{name}' (may not have been executed yet)"
            )
            click.echo(f"Expected log group: {log_group_name}\n")
            sys.exit(1)

        if follow:
            click.echo("\nFollowing logs (Press Ctrl+C to stop)...\n")
            _follow_logs(logs_client, log_group_name)
        else:
            click.echo("\nFetching recent logs...\n")
            _fetch_logs(logs_client, log_group_name)

    except KeyboardInterrupt:
        click.echo("\n\nStopped following logs")
        sys.exit(0)
    except Exception as e:
        click.echo(f"\nError: {str(e)}")
        sys.exit(1)


def _fetch_logs(logs_client, log_group_name: str) -> None:
    start_time = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
    end_time = int(datetime.now().timestamp() * 1000)

    try:
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=start_time,
            endTime=end_time,
            limit=100,
            interleaved=True,
        )

        events = response.get("events", [])

        if not events:
            click.echo("No log entries found in the past hour")
            return

        click.echo("=" * 80)
        click.echo(f"Logs for MCP server (showing {len(events)} entries)")
        click.echo("=" * 80 + "\n")

        for event in events:
            timestamp = datetime.fromtimestamp(event["timestamp"] / 1000)
            message = event["message"].rstrip()

            time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            click.echo(f"[{time_str}] {message}")

        click.echo("\n" + "=" * 80)
        click.echo(f"End of logs ({len(events)} entries)")
        click.echo("=" * 80 + "\n")

    except logs_client.exceptions.ResourceNotFoundException:
        click.echo(f"Error: Log group '{log_group_name}' not found")
        click.echo("The MCP server may not have been executed yet")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error fetching logs: {str(e)}")
        sys.exit(1)


def _follow_logs(logs_client, log_group_name: str) -> None:
    import time

    last_timestamp = int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
    seen_event_ids = set()

    click.echo("=" * 80)
    click.echo("Following logs for MCP server")
    click.echo("=" * 80 + "\n")

    try:
        while True:
            try:
                response = logs_client.filter_log_events(
                    logGroupName=log_group_name,
                    startTime=last_timestamp,
                    interleaved=True,
                )
                events = response.get("events", [])

                for event in events:
                    event_id = event["eventId"]
                    if event_id in seen_event_ids:
                        continue

                    seen_event_ids.add(event_id)
                    timestamp = datetime.fromtimestamp(event["timestamp"] / 1000)
                    message = event["message"].rstrip()

                    time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    click.echo(f"[{time_str}] {message}")

                    if event["timestamp"] > last_timestamp:
                        last_timestamp = event["timestamp"]

            except logs_client.exceptions.ResourceNotFoundException:
                click.echo(f"\nError: Log group '{log_group_name}' not found")
                click.echo("The MCP server may not have been executed yet")
                sys.exit(1)
            except Exception as e:
                click.echo(f"\nError following logs: {str(e)}")

            time.sleep(2)

    except KeyboardInterrupt:
        raise
