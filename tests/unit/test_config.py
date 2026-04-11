from unittest.mock import patch

import pytest

from superbox.shared.config import Config, get_env, load_env


class TestGetEnv:
    def test_returns_value_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_KEY", "hello")
        assert get_env("TEST_KEY") == "hello"

    def test_raises_value_error_when_key_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MISSING_KEY", raising=False)
        with pytest.raises(ValueError, match="MISSING_KEY"):
            get_env("MISSING_KEY")

    def test_error_message_includes_key_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANOTHER_KEY", raising=False)
        with pytest.raises(ValueError, match="Required environment variable"):
            get_env("ANOTHER_KEY")


class TestLoadEnv:
    def test_loads_dotenv_when_file_exists(self, tmp_path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("DUMMY=1\n")
        with patch("superbox.shared.config.load_dotenv") as mock_ld:
            load_env(env_file)
            mock_ld.assert_called_once_with(env_file)

    def test_skips_when_file_does_not_exist(self, tmp_path) -> None:
        with patch("superbox.shared.config.load_dotenv") as mock_ld:
            load_env(tmp_path / "nonexistent.env")
            mock_ld.assert_not_called()

    def test_defaults_to_cwd_dotenv_when_no_path_given(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("X=1\n")
        with patch("superbox.shared.config.load_dotenv") as mock_ld:
            load_env()
            mock_ld.assert_called_once()

    def test_accepts_string_path(self, tmp_path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("Z=1\n")
        with patch("superbox.shared.config.load_dotenv") as mock_ld:
            load_env(str(env_file))
            mock_ld.assert_called_once()


class TestConfig:
    def test_reads_api_and_cloudflare_vars(self) -> None:
        cfg = Config()
        assert cfg.SUPERBOX_API_URL == "http://localhost:8000/api/v1"
        assert cfg.CLOUDFLARE_ACCOUNT_ID == "fake-account-id"
        assert cfg.CLOUDFLARE_R2_ACCESS_KEY_ID == "testing"
        assert cfg.CLOUDFLARE_R2_BUCKET_NAME == "test-superbox-registry"
        assert cfg.CLOUDFLARE_WORKER_URL.startswith("https://")

    def test_reads_firebase_vars(self) -> None:
        cfg = Config()
        assert cfg.FIREBASE_API_KEY == "fake-firebase-key"
        assert cfg.FIREBASE_PROJECT_ID == "fake-project"

    def test_reads_scanner_vars(self) -> None:
        cfg = Config()
        assert cfg.SONAR_TOKEN == "fake-sonar-token"
        assert cfg.SONAR_ORGANIZATION == "fake-org"
        assert cfg.SNYK_API_TOKEN == "fake-snyk-token"
        assert cfg.GITGUARDIAN_API_KEY == "fake-gg-key"

    def test_reads_razorpay_vars(self) -> None:
        cfg = Config()
        assert cfg.RAZORPAY_KEY_ID == "fake-rzp-key"
        assert cfg.RAZORPAY_KEY_SECRET == "fake-rzp-secret"

    def test_optional_oauth_fields_are_none_when_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for key in (
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
            "GITHUB_CLIENT_ID",
            "GITHUB_CLIENT_SECRET",
        ):
            monkeypatch.delenv(key, raising=False)
        cfg = Config()
        assert cfg.GOOGLE_CLIENT_ID is None
        assert cfg.GOOGLE_CLIENT_SECRET is None
        assert cfg.GITHUB_CLIENT_ID is None
        assert cfg.GITHUB_CLIENT_SECRET is None

    def test_optional_oauth_fields_populated_when_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "gcid")
        monkeypatch.setenv("GITHUB_CLIENT_ID", "ghcid")
        cfg = Config()
        assert cfg.GOOGLE_CLIENT_ID == "gcid"
        assert cfg.GITHUB_CLIENT_ID == "ghcid"


class TestValidateServer:
    def test_passes_with_all_required_vars(self) -> None:
        assert Config().validate_server() is True

    def test_raises_on_missing_firebase_key(self) -> None:
        cfg = Config()
        cfg.FIREBASE_API_KEY = None
        with pytest.raises(ValueError, match="FIREBASE_API_KEY"):
            cfg.validate_server()

    def test_raises_on_missing_razorpay_key_id(self) -> None:
        cfg = Config()
        cfg.RAZORPAY_KEY_ID = None
        with pytest.raises(ValueError, match="RAZORPAY_KEY_ID"):
            cfg.validate_server()

    def test_raises_on_empty_string_value(self) -> None:
        cfg = Config()
        cfg.CLOUDFLARE_ACCOUNT_ID = ""
        with pytest.raises(ValueError, match="CLOUDFLARE_ACCOUNT_ID"):
            cfg.validate_server()

    def test_error_message_lists_all_missing_fields(self) -> None:
        cfg = Config()
        cfg.FIREBASE_API_KEY = None
        cfg.RAZORPAY_KEY_ID = None
        with pytest.raises(ValueError) as exc_info:
            cfg.validate_server()
        msg = str(exc_info.value)
        assert "FIREBASE_API_KEY" in msg
        assert "RAZORPAY_KEY_ID" in msg


class TestValidateCli:
    def test_passes_with_all_required_vars(self) -> None:
        assert Config().validate_cli() is True

    def test_raises_on_missing_sonar_token(self) -> None:
        cfg = Config()
        cfg.SONAR_TOKEN = None
        with pytest.raises(ValueError, match="SONAR_TOKEN"):
            cfg.validate_cli()

    def test_raises_on_missing_snyk_token(self) -> None:
        cfg = Config()
        cfg.SNYK_API_TOKEN = None
        with pytest.raises(ValueError, match="SNYK_API_TOKEN"):
            cfg.validate_cli()

    def test_raises_on_missing_gitguardian_key(self) -> None:
        cfg = Config()
        cfg.GITGUARDIAN_API_KEY = None
        with pytest.raises(ValueError, match="GITGUARDIAN_API_KEY"):
            cfg.validate_cli()

    def test_does_not_require_razorpay(self) -> None:
        cfg = Config()
        cfg.RAZORPAY_KEY_ID = None
        cfg.RAZORPAY_KEY_SECRET = None
        assert cfg.validate_cli() is True
