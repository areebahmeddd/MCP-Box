from unittest.mock import patch

import pytest

from superbox.shared.config import Config, get_env, load_env


class TestGetEnv:
    def test_returns_value_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SOME_KEY", "hello")
        assert get_env("SOME_KEY") == "hello"

    def test_raises_when_key_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEFINITELY_MISSING", raising=False)
        with pytest.raises(ValueError, match="DEFINITELY_MISSING"):
            get_env("DEFINITELY_MISSING")


class TestLoadEnv:
    def test_calls_load_dotenv_with_correct_path(self, tmp_path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("DUMMY=1\n")
        with patch("superbox.shared.config.load_dotenv") as mock_ld:
            load_env(env_file)
            mock_ld.assert_called_once_with(env_file)

    def test_skips_when_file_does_not_exist(self, tmp_path) -> None:
        with patch("superbox.shared.config.load_dotenv") as mock_ld:
            load_env(tmp_path / "nonexistent.env")
            mock_ld.assert_not_called()

    def test_defaults_to_cwd_dotenv(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text("X=1\n")
        with patch("superbox.shared.config.load_dotenv") as mock_ld:
            load_env()
            mock_ld.assert_called_once()


class TestConfig:
    def test_reads_all_aws_and_api_vars(self) -> None:
        cfg = Config()
        assert cfg.SUPERBOX_API_URL == "http://localhost:8000/api/v1"
        assert cfg.AWS_REGION == "ap-south-1"
        assert cfg.AWS_ACCESS_KEY_ID == "testing"
        assert cfg.S3_BUCKET_NAME == "test-superbox-registry"
        assert cfg.WEBSOCKET_URL.startswith("wss://")

    def test_reads_firebase_vars(self) -> None:
        cfg = Config()
        assert cfg.FIREBASE_API_KEY == "fake-firebase-key"
        assert cfg.FIREBASE_PROJECT_ID == "fake-project"

    def test_reads_scanner_vars(self) -> None:
        cfg = Config()
        assert cfg.SONAR_TOKEN == "fake-sonar-token"
        assert cfg.GITGUARDIAN_API_KEY == "fake-gg-key"

    def test_validate_server_passes_with_all_vars(self) -> None:
        assert Config().validate_server() is True

    def test_validate_server_raises_on_missing_field(self) -> None:
        cfg = Config()
        cfg.FIREBASE_API_KEY = None  # simulate missing
        with pytest.raises(ValueError, match="FIREBASE_API_KEY"):
            cfg.validate_server()

    def test_validate_server_raises_on_missing_razorpay(self) -> None:
        cfg = Config()
        cfg.RAZORPAY_KEY_ID = None
        with pytest.raises(ValueError, match="RAZORPAY_KEY_ID"):
            cfg.validate_server()

    def test_validate_cli_passes_with_all_vars(self) -> None:
        assert Config().validate_cli() is True

    def test_validate_cli_raises_on_missing_scanner(self) -> None:
        cfg = Config()
        cfg.SONAR_TOKEN = None
        with pytest.raises(ValueError, match="SONAR_TOKEN"):
            cfg.validate_cli()

    def test_validate_cli_raises_on_missing_snyk(self) -> None:
        cfg = Config()
        cfg.SNYK_API_TOKEN = None
        with pytest.raises(ValueError, match="SNYK_API_TOKEN"):
            cfg.validate_cli()
