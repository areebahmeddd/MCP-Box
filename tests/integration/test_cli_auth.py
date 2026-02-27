import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from superbox.cli.commands.auth import auth


def _firebase_ok(email: str = "user@example.com") -> MagicMock:
    """Return a mock requests.Response that simulates successful Firebase auth."""
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


def _lookup_ok(email: str = "user@example.com", uid: str = "uid-001") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"users": [{"email": email, "localId": uid, "emailVerified": True}]}
    return resp


class TestAuthLogin:
    def test_email_login_success_saves_auth_file(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        # AUTH_FILE does not exist → _session_active short-circuits with False
        # so only ONE requests.post call happens: signInWithPassword
        with (
            patch("superbox.cli.commands.auth.AUTH_FILE", auth_path),
            patch("superbox.cli.commands.auth.requests.post", return_value=_firebase_ok()),
        ):
            result = runner.invoke(
                auth,
                [
                    "login",
                    "--provider",
                    "email",
                    "--email",
                    "user@example.com",
                    "--password",
                    "secret",
                ],
            )
        assert result.exit_code == 0, result.output
        assert "successful" in result.output.lower()
        saved = json.loads(auth_path.read_text())
        assert saved["id_token"] == "tok-abc"
        assert saved["provider"] == "password"

    def test_email_login_firebase_error_shows_message(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        # AUTH_FILE does not exist → only one request: signInWithPassword → fails
        with (
            patch("superbox.cli.commands.auth.AUTH_FILE", auth_path),
            patch(
                "superbox.cli.commands.auth.requests.post",
                return_value=_firebase_err("INVALID_PASSWORD"),
            ),
        ):
            result = runner.invoke(
                auth,
                [
                    "login",
                    "--provider",
                    "email",
                    "--email",
                    "user@example.com",
                    "--password",
                    "wrong",
                ],
            )
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "invalid" in result.output.lower()

    def test_already_logged_in_skips_login(self, tmp_path: Path) -> None:
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


class TestAuthStatus:
    def test_not_logged_in(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "no-auth.json"  # does not exist
        with patch("superbox.cli.commands.auth.AUTH_FILE", auth_path):
            result = runner.invoke(auth, ["status"])
        assert "not logged in" in result.output.lower()

    def test_logged_in_shows_email(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        auth_path.parent.mkdir(parents=True, exist_ok=True)
        auth_path.write_text(
            json.dumps(
                {
                    "id_token": "tok",
                    "provider": "password",
                }
            )
        )
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


class TestAuthLogout:
    def test_logout_removes_auth_file(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        auth_path.parent.mkdir(parents=True, exist_ok=True)
        auth_path.write_text("{}")
        with patch("superbox.cli.commands.auth.AUTH_FILE", auth_path):
            result = runner.invoke(auth, ["logout"])
        assert result.exit_code == 0
        assert not auth_path.exists()
        assert "logged out" in result.output.lower()

    def test_logout_when_not_logged_in(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "no-file.json"
        with patch("superbox.cli.commands.auth.AUTH_FILE", auth_path):
            result = runner.invoke(auth, ["logout"])
        assert result.exit_code == 0
        assert "no credentials" in result.output.lower()


class TestAuthRefresh:
    def test_refresh_updates_tokens(self, tmp_path: Path) -> None:
        runner = CliRunner()
        auth_path = tmp_path / "auth.json"
        auth_path.parent.mkdir(parents=True, exist_ok=True)
        auth_path.write_text(
            json.dumps(
                {
                    "id_token": "old-tok",
                    "refresh_token": "old-ref",
                }
            )
        )
        new_tokens = MagicMock()
        new_tokens.status_code = 200
        new_tokens.json.return_value = {
            "id_token": "new-tok",
            "refresh_token": "new-ref",
            "expires_in": "3600",
            "user_id": "uid-001",
        }
        with (
            patch("superbox.cli.commands.auth.AUTH_FILE", auth_path),
            patch("superbox.cli.commands.auth.requests.post", return_value=new_tokens),
        ):
            result = runner.invoke(auth, ["refresh"])
        assert result.exit_code == 0
        saved = json.loads(auth_path.read_text())
        assert saved["id_token"] == "new-tok"

    def test_refresh_fails_without_token_file(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with patch("superbox.cli.commands.auth.AUTH_FILE", tmp_path / "missing.json"):
            result = runner.invoke(auth, ["refresh"])
        assert result.exit_code != 0
        assert "login" in result.output.lower() or "refresh token" in result.output.lower()
