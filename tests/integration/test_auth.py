import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from superbox.cli.commands.auth import auth


def _firebase_ok(email: str = "user@example.com") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "idToken": "tok-abc",
        "refreshToken": "ref-abc",
        "expiresIn": "3600",
        "email": email,
        "localId": "uid-001",
    }
    return resp


def _firebase_err(message: str = "INVALID_PASSWORD") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 400
    resp.json.return_value = {"error": {"message": message}}
    resp.text = message
    return resp


def _lookup_ok(email: str = "user@example.com") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "users": [{"email": email, "localId": "uid-001", "emailVerified": True}]
    }
    return resp


def _lookup_with_name(name: str = "Bob") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"users": [{"displayName": name, "localId": "uid"}]}
    return resp


class TestAuthLogin:
    def test_email_login_saves_tokens_and_prints_success(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        with (
            patch("superbox.cli.commands.auth.AUTH_FILE", auth_path),
            patch("superbox.cli.commands.auth.requests.post", return_value=_firebase_ok()),
        ):
            result = runner.invoke(
                auth, ["login", "--provider", "email", "--email", "u@x.com", "--password", "pw"]
            )
        assert result.exit_code == 0, result.output
        assert "successful" in result.output.lower()
        saved = json.loads(auth_path.read_text())
        assert saved["id_token"] == "tok-abc"
        assert saved["provider"] == "password"

    def test_email_login_stores_display_name_from_lookup(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        with (
            patch("superbox.cli.commands.auth.AUTH_FILE", auth_path),
            patch(
                "superbox.cli.commands.auth.requests.post",
                side_effect=[_firebase_ok(), _lookup_with_name("Alice")],
            ),
        ):
            result = runner.invoke(
                auth, ["login", "--provider", "email", "--email", "u@x.com", "--password", "pw"]
            )
        assert result.exit_code == 0
        saved = json.loads(auth_path.read_text())
        assert saved["name"] == "Alice"

    def test_firebase_error_shows_message_and_exits_nonzero(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        with (
            patch("superbox.cli.commands.auth.AUTH_FILE", auth_path),
            patch(
                "superbox.cli.commands.auth.requests.post",
                return_value=_firebase_err("INVALID_PASSWORD"),
            ),
        ):
            result = runner.invoke(
                auth, ["login", "--provider", "email", "--email", "u@x.com", "--password", "wrong"]
            )
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "invalid" in result.output.lower()

    def test_non_json_error_response_handled(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        err_resp = MagicMock()
        err_resp.status_code = 400
        err_resp.json.side_effect = ValueError("no JSON")
        err_resp.text = "Bad Request"
        with (
            patch("superbox.cli.commands.auth.AUTH_FILE", auth_path),
            patch("superbox.cli.commands.auth.requests.post", return_value=err_resp),
        ):
            result = runner.invoke(
                auth, ["login", "--provider", "email", "--email", "a@b.com", "--password", "pw"]
            )
        assert result.exit_code != 0

    def test_already_logged_in_skips_new_login(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        auth_path.parent.mkdir(parents=True, exist_ok=True)
        auth_path.write_text(json.dumps({"id_token": "existing-tok"}))
        with (
            patch("superbox.cli.commands.auth.AUTH_FILE", auth_path),
            patch("superbox.cli.commands.auth.requests.post", return_value=_lookup_ok()),
        ):
            result = runner.invoke(auth, ["login", "--provider", "email"])
        assert "already logged in" in result.output.lower()

    def test_network_error_during_login_exits_nonzero(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        with (
            patch("superbox.cli.commands.auth.AUTH_FILE", auth_path),
            patch(
                "superbox.cli.commands.auth.requests.post", side_effect=Exception("network down")
            ),
        ):
            result = runner.invoke(
                auth, ["login", "--provider", "email", "--email", "u@x.com", "--password", "pw"]
            )
        assert result.exit_code != 0


class TestAuthStatus:
    def test_not_logged_in_shows_message(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("superbox.cli.commands.auth.AUTH_FILE", tmp_path / "no-auth.json"):
            result = runner.invoke(auth, ["status"])
        assert "not logged in" in result.output.lower()

    def test_corrupt_auth_file_shows_not_logged_in(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        auth_path.write_text("{invalid json")
        with patch("superbox.cli.commands.auth.AUTH_FILE", auth_path):
            result = runner.invoke(auth, ["status"])
        assert "not logged in" in result.output.lower()

    def test_logged_in_shows_email(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps({"id_token": "tok", "provider": "password"}))
        with (
            patch("superbox.cli.commands.auth.AUTH_FILE", auth_path),
            patch(
                "superbox.cli.commands.auth.requests.post",
                return_value=_lookup_ok("user@example.com"),
            ),
        ):
            result = runner.invoke(auth, ["status"])
        assert "logged in" in result.output.lower()
        assert "user@example.com" in result.output

    def test_invalid_stored_token_shows_invalid_message(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps({"id_token": "expired-tok"}))
        bad_resp = MagicMock()
        bad_resp.status_code = 400
        bad_resp.json.return_value = {"error": {"message": "INVALID_ID_TOKEN"}}
        bad_resp.text = "INVALID_ID_TOKEN"
        with (
            patch("superbox.cli.commands.auth.AUTH_FILE", auth_path),
            patch("superbox.cli.commands.auth.requests.post", return_value=bad_resp),
        ):
            result = runner.invoke(auth, ["status"])
        assert "invalid" in result.output.lower() or "credentials" in result.output.lower()


class TestAuthLogout:
    def test_logout_removes_auth_file(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps({"id_token": "tok"}))
        with patch("superbox.cli.commands.auth.AUTH_FILE", auth_path):
            result = runner.invoke(auth, ["logout"])
        assert result.exit_code == 0
        assert "logged out" in result.output.lower()
        assert not auth_path.exists()

    def test_logout_when_no_file_shows_no_credentials(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("superbox.cli.commands.auth.AUTH_FILE", tmp_path / "no-auth.json"):
            result = runner.invoke(auth, ["logout"])
        assert result.exit_code == 0
        assert "no credentials" in result.output.lower()


class TestAuthRefresh:
    def test_no_auth_file_exits_with_message(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("superbox.cli.commands.auth.AUTH_FILE", tmp_path / "no-auth.json"):
            result = runner.invoke(auth, ["refresh"])
        assert result.exit_code != 0
        assert "login" in result.output.lower() or "refresh token" in result.output.lower()

    def test_auth_file_without_refresh_token_exits(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps({"id_token": "tok"}))
        with patch("superbox.cli.commands.auth.AUTH_FILE", auth_path):
            result = runner.invoke(auth, ["refresh"])
        assert result.exit_code != 0
        assert "refresh token" in result.output.lower()

    def test_successful_refresh_updates_and_saves_token(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(
            json.dumps({"id_token": "old-tok", "refresh_token": "ref-tok", "provider": "password"})
        )
        refresh_resp = MagicMock()
        refresh_resp.status_code = 200
        refresh_resp.json.return_value = {
            "id_token": "new-tok",
            "refresh_token": "new-ref-tok",
            "expires_in": "3600",
            "user_id": "uid-001",
        }
        with (
            patch("superbox.cli.commands.auth.AUTH_FILE", auth_path),
            patch("superbox.cli.commands.auth.requests.post", return_value=refresh_resp),
        ):
            result = runner.invoke(auth, ["refresh"])
        assert result.exit_code == 0
        assert "refreshed" in result.output.lower()
        saved = json.loads(auth_path.read_text())
        assert saved["id_token"] == "new-tok"

    def test_api_error_during_refresh_exits_nonzero(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        auth_path.write_text(json.dumps({"id_token": "tok", "refresh_token": "ref"}))
        error_resp = MagicMock()
        error_resp.status_code = 400
        error_resp.json.return_value = {"error": {"message": "TOKEN_EXPIRED"}}
        error_resp.text = "TOKEN_EXPIRED"
        with (
            patch("superbox.cli.commands.auth.AUTH_FILE", auth_path),
            patch("superbox.cli.commands.auth.requests.post", return_value=error_resp),
        ):
            result = runner.invoke(auth, ["refresh"])
        assert result.exit_code != 0
