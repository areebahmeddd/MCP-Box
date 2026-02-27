import io
import json
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest

from superbox.aws.proxy import proxy


class FakeWebSocket:
    """
    Minimal async-compatible WebSocket double.
    Yields `server_messages` when iterated, records everything sent via .send().
    """

    def __init__(self, server_messages: list[str]) -> None:
        self._messages = list(server_messages)
        self._sent: list[dict] = []

    async def send(self, data: str) -> None:
        self._sent.append(json.loads(data))

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)


def _make_connect(ws: FakeWebSocket):
    """Return an async context manager that yields the given FakeWebSocket."""

    @asynccontextmanager
    async def _connect(url, **kwargs):
        yield ws

    return _connect


class TestProxy:
    async def test_tags_mcp_name_on_outgoing_message(self) -> None:
        """Every message forwarded to WS must include _mcp_name from the URL."""
        ws = FakeWebSocket(server_messages=[])
        input_line = json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1}) + "\n"
        url = "wss://example.com/production?name=weather-mcp"

        with (
            patch("superbox.aws.proxy.websockets.connect", _make_connect(ws)),
            patch("sys.stdin") as mock_stdin,
            patch("sys.stdout", new_callable=io.StringIO),
        ):
            mock_stdin.readline.side_effect = [input_line, ""]
            await proxy(url)

        assert len(ws._sent) == 1
        msg = ws._sent[0]
        assert msg["_mcp_name"] == "weather-mcp"
        assert msg["method"] == "tools/list"
        assert msg["id"] == 1

    async def test_writes_server_response_to_stdout(self) -> None:
        """Messages received from WS must be written to stdout."""
        server_msg = json.dumps({"jsonrpc": "2.0", "result": {"tools": []}, "id": 1})
        ws = FakeWebSocket(server_messages=[server_msg])
        url = "wss://example.com/production?name=weather-mcp"
        captured_stdout = io.StringIO()

        with (
            patch("superbox.aws.proxy.websockets.connect", _make_connect(ws)),
            patch("sys.stdin") as mock_stdin,
            patch("sys.stdout", captured_stdout),
        ):
            mock_stdin.readline.return_value = ""  # stdin EOF immediately
            await proxy(url)

        output = captured_stdout.getvalue()
        assert "tools" in output

    async def test_invalid_json_from_stdin_is_skipped(self) -> None:
        """Non-JSON stdin lines should not crash the proxy."""
        ws = FakeWebSocket(server_messages=[])
        url = "wss://example.com/production?name=weather-mcp"

        with (
            patch("superbox.aws.proxy.websockets.connect", _make_connect(ws)),
            patch("sys.stdin") as mock_stdin,
            patch("sys.stdout", new_callable=io.StringIO),
            patch("sys.stderr", new_callable=io.StringIO),
        ):
            mock_stdin.readline.side_effect = ["not json\n", ""]
            await proxy(url)  # must not raise

        assert ws._sent == []  # nothing forwarded

    async def test_missing_name_in_url_raises_sysexit(self) -> None:
        """URL without ?name= param must exit with code 1."""
        url = "wss://example.com/production"  # no ?name=

        with pytest.raises(SystemExit) as exc_info:
            await proxy(url)
        assert exc_info.value.code == 1

    async def test_connection_error_raises_sysexit(self) -> None:
        """A WebSocket connection failure must exit with code 1."""
        url = "wss://example.com/production?name=fail-mcp"

        async def broken_connect(url, **kwargs):
            raise ConnectionError("refused")

        # make it a context manager that raises on __aenter__
        @asynccontextmanager
        async def broken_cm(url, **kwargs):
            raise ConnectionError("refused")
            yield  # unreachable

        with (
            patch("superbox.aws.proxy.websockets.connect", broken_cm),
            patch("sys.stderr", new_callable=io.StringIO),
        ):
            with pytest.raises(SystemExit) as exc_info:
                await proxy(url)
        assert exc_info.value.code == 1
