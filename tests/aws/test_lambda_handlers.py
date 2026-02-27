import importlib
import io
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import via importlib because `lambda` is a reserved keyword
lm = importlib.import_module("superbox.aws.lambda")


@pytest.fixture(autouse=True)
def reset_lambda_globals() -> None:
    """Reset global mutable state between every test."""
    lm._mcp_process = None
    lm._repo_dir = None
    lm._connection_params = {}
    yield
    # cleanup: kill any lingering process
    if lm._mcp_process is not None:
        try:
            lm._mcp_process.kill()
        except Exception:
            pass
    lm._mcp_process = None
    lm._repo_dir = None
    lm._connection_params = {}


def _make_event(
    route: str, connection_id: str = "conn-001", query_params: dict | None = None, body: str = ""
) -> dict:
    """Build a minimal API Gateway WebSocket event."""
    return {
        "requestContext": {
            "routeKey": route,
            "connectionId": connection_id,
            "domainName": "example.execute-api.ap-south-1.amazonaws.com",
            "stage": "production",
        },
        "queryStringParameters": query_params or {},
        "body": body,
    }


def _make_mock_process(responses: list[bytes]) -> MagicMock:
    """Return a mock subprocess.Popen with preset stdout readline responses."""
    proc = MagicMock()
    proc.poll.return_value = None  # process is alive
    proc.stdin = MagicMock()
    proc.stdout.readline.side_effect = responses
    return proc


class TestHandleConnect:
    def test_returns_200_and_stores_params(self) -> None:
        event = _make_event("$connect", query_params={"name": "weather-mcp"})
        response = lm.handle_connect(event)
        assert response["statusCode"] == 200
        assert lm._connection_params["conn-001"]["name"] == "weather-mcp"

    def test_returns_400_when_name_missing(self) -> None:
        event = _make_event("$connect", query_params={})
        response = lm.handle_connect(event)
        assert response["statusCode"] == 400
        assert lm._connection_params == {}  # nothing stored

    def test_stores_extra_query_params(self) -> None:
        event = _make_event(
            "$connect",
            query_params={
                "name": "test-mcp",
                "test_mode": "true",
                "repo_url": "https%3A//github.com/a/b",
            },
        )
        lm.handle_connect(event)
        assert lm._connection_params["conn-001"]["test_mode"] == "true"


class TestHandleDisconnect:
    def test_returns_200(self) -> None:
        event = _make_event("$disconnect")
        assert lm.handle_disconnect(event)["statusCode"] == 200

    def test_kills_running_process(self) -> None:
        mock_proc = MagicMock()
        lm._mcp_process = mock_proc
        lm.handle_disconnect(_make_event("$disconnect"))
        mock_proc.kill.assert_called_once()
        assert lm._mcp_process is None

    def test_removes_repo_dir(self, tmp_path: Path) -> None:
        fake_repo = tmp_path / "repo"
        fake_repo.mkdir()
        lm._repo_dir = str(fake_repo)
        lm.handle_disconnect(_make_event("$disconnect"))
        assert lm._mcp_process is None
        assert lm._repo_dir is None

    def test_no_process_no_error(self) -> None:
        """Should not raise when there is no active process."""
        lm._mcp_process = None
        lm.handle_disconnect(_make_event("$disconnect"))  # must not raise


class TestLambdaHandler:
    def test_routes_connect(self) -> None:
        with patch.object(lm, "handle_connect", return_value={"statusCode": 200}) as mock:
            lm.lambda_handler(_make_event("$connect"), {})
            mock.assert_called_once()

    def test_routes_disconnect(self) -> None:
        with patch.object(lm, "handle_disconnect", return_value={"statusCode": 200}) as mock:
            lm.lambda_handler(_make_event("$disconnect"), {})
            mock.assert_called_once()

    def test_routes_default(self) -> None:
        with patch.object(lm, "handle_message", return_value={"statusCode": 200}) as mock:
            lm.lambda_handler(_make_event("$default"), {})
            mock.assert_called_once()

    def test_unknown_route_returns_400(self) -> None:
        response = lm.lambda_handler(_make_event("$unknown"), {})
        assert response["statusCode"] == 400


class TestHandleMessageColdStart:
    def test_initializes_server_and_sends_response(self) -> None:
        init_resp = json.dumps({"jsonrpc": "2.0", "id": 0, "result": {}}).encode() + b"\n"
        tool_resp = (
            json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}).encode() + b"\n"
        )
        mock_proc = _make_mock_process([init_resp, tool_resp])

        mock_apigw = MagicMock()
        body = json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1})
        event = _make_event("$default", body=body, query_params={"name": "weather-mcp"})
        lm._connection_params["conn-001"] = {"name": "weather-mcp"}

        metadata = {
            "repository": {"url": "https://github.com/test/weather-mcp"},
            "entrypoint": "main.py",
            "lang": "python",
        }

        with (
            patch.object(lm, "fetch_meta", return_value=metadata),
            patch.object(lm, "clone_repo", return_value="/tmp/repo"),
            patch.object(lm, "install_deps"),
            patch.object(lm, "start_server", return_value=mock_proc),
            patch("superbox.aws.lambda.boto3.client", return_value=mock_apigw),
        ):
            response = lm.handle_message(event)

        assert response["statusCode"] == 200
        mock_apigw.post_to_connection.assert_called_once()

    def test_warm_process_reused(self) -> None:
        """When _mcp_process is already running, skip setup entirely."""
        tool_resp = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}}).encode() + b"\n"
        mock_proc = _make_mock_process([tool_resp])
        lm._mcp_process = mock_proc

        mock_apigw = MagicMock()
        body = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 1})
        event = _make_event("$default", body=body)
        lm._connection_params["conn-001"] = {"name": "weather-mcp"}

        with (
            patch.object(lm, "fetch_meta") as mock_fetch,
            patch("superbox.aws.lambda.boto3.client", return_value=mock_apigw),
        ):
            lm.handle_message(event)
            # fetch_meta should NOT be called — warm path
            mock_fetch.assert_not_called()


class TestFetchMeta:
    def test_returns_metadata_from_s3(self) -> None:
        metadata = {"repository": {"url": "https://github.com/test/mcp"}, "entrypoint": "main.py"}

        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": io.BytesIO(json.dumps(metadata).encode())}

        with patch("superbox.aws.lambda.boto3.client", return_value=mock_s3):
            result = lm.fetch_meta("test-mcp")

        assert result["repository"]["url"] == "https://github.com/test/mcp"

    def test_raises_on_s3_failure(self) -> None:
        """Any S3 error propagates as an Exception."""
        mock_s3 = MagicMock()
        # Use a real exception class so boto3 exception-class checks inside
        # fetch_meta don't cause TypeError
        NoSuchKey = type("NoSuchKey", (Exception,), {})
        mock_s3.exceptions.NoSuchKey = NoSuchKey
        mock_s3.get_object.side_effect = NoSuchKey("The specified key does not exist")

        with patch("superbox.aws.lambda.boto3.client", return_value=mock_s3):
            with pytest.raises(Exception):
                lm.fetch_meta("nonexistent")


class TestCloneRepo:
    def test_clones_github_repo(self, tmp_path: Path) -> None:
        """clone_repo downloads a ZIP and extracts it; mock urllib and zipfile."""
        # Create a fake ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("repo-main/main.py", 'print("hello")\n')
        zip_bytes = zip_buffer.getvalue()

        def fake_urlretrieve(url, dest):
            Path(dest).write_bytes(zip_bytes)

        with (
            patch("superbox.aws.lambda.urllib.request.urlretrieve", side_effect=fake_urlretrieve),
            patch("superbox.aws.lambda.tempfile.mkdtemp", return_value=str(tmp_path)),
        ):
            result = lm.clone_repo("https://github.com/test/repo", "test-mcp")

        assert result is not None
        assert "repo" in result

    def test_raises_on_non_github_url(self) -> None:
        with pytest.raises(Exception, match="GitHub"):
            lm.clone_repo("https://gitlab.com/test/repo", "test-mcp")


class TestInstallDeps:
    def test_skips_when_no_requirements_file(self, tmp_path: Path) -> None:
        """Should not call pip when requirements.txt is absent."""
        with patch("superbox.aws.lambda.subprocess.run") as mock_run:
            lm.install_deps(str(tmp_path))
            mock_run.assert_not_called()

    def test_calls_pip_when_requirements_exist(self, tmp_path: Path) -> None:
        (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("superbox.aws.lambda.subprocess.run", return_value=mock_result) as mock_run:
            lm.install_deps(str(tmp_path))
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "pip" in args or "install" in args
