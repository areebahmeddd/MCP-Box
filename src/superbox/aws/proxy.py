import sys
import asyncio
import argparse
import json
from urllib.parse import urlparse, parse_qs
import websockets


async def proxy(ws_url):
    """Connect to WebSocket and bridge with stdio."""
    parsed_url = urlparse(ws_url)
    query_params = parse_qs(parsed_url.query)
    mcp_name = query_params.get("name", [None])[0]

    if not mcp_name:
        print("Error: MCP name not provided in WebSocket URL", file=sys.stderr)
        sys.exit(1)

    try:
        async with websockets.connect(ws_url) as websocket:

            async def read_stdin():
                """Read from stdin and send to WebSocket."""
                loop = asyncio.get_event_loop()
                while True:
                    line = await loop.run_in_executor(None, sys.stdin.readline)
                    if not line:
                        break

                    try:
                        message = json.loads(line.strip())
                        message["_mcp_name"] = mcp_name
                        await websocket.send(json.dumps(message))
                    except json.JSONDecodeError as e:
                        print(f"Error: Invalid JSON-RPC message: {e}", file=sys.stderr)

            async def read_websocket():
                """Read from WebSocket and write to stdout."""
                async for message in websocket:
                    sys.stdout.write(message + "\n")
                    sys.stdout.flush()

            await asyncio.gather(read_stdin(), read_websocket())

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="SuperBox MCP WebSocket Proxy")
    parser.add_argument("--url", required=True, help="WebSocket URL")
    args = parser.parse_args()

    asyncio.run(proxy(args.url))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
