import json
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

FAKE_ENV: dict[str, str] = {
    "SUPERBOX_API_URL": "http://localhost:8000/api/v1",
    "AWS_REGION": "ap-south-1",
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "S3_BUCKET_NAME": "test-superbox-registry",
    "WEBSOCKET_URL": "wss://example.execute-api.ap-south-1.amazonaws.com/production",
    "FIREBASE_API_KEY": "fake-firebase-key",
    "FIREBASE_PROJECT_ID": "fake-project",
    "SONAR_TOKEN": "fake-sonar-token",
    "SONAR_ORGANIZATION": "fake-org",
    "SNYK_API_TOKEN": "fake-snyk-token",
    "GITGUARDIAN_API_KEY": "fake-gg-key",
    "RAZORPAY_KEY_ID": "fake-rzp-key",
    "RAZORPAY_KEY_SECRET": "fake-rzp-secret",
}

# Rendered .env file content used by CLI commands that read from cwd/.env
FAKE_ENV_CONTENT: str = "\n".join(f"{k}={v}" for k, v in FAKE_ENV.items()) + "\n"


@pytest.fixture(autouse=True)
def set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject all required environment variables for every test."""
    for key, value in FAKE_ENV.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def s3_bucket():
    """
    Start a moto-mocked AWS session, create the test bucket, and yield its name.
    The mock is torn down automatically after each test.
    """
    with mock_aws():
        client = boto3.client("s3", region_name="ap-south-1")
        bucket_name = FAKE_ENV["S3_BUCKET_NAME"]
        client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "ap-south-1"},
        )
        yield bucket_name


@pytest.fixture
def sample_server() -> dict:
    """Return a complete, valid MCP server payload."""
    return {
        "name": "weather-mcp",
        "version": "1.0.0",
        "description": "Fetch weather data via MCP",
        "author": "test-author",
        "lang": "python",
        "license": "MIT",
        "entrypoint": "main.py",
        "repository": {"type": "git", "url": "https://github.com/test/weather-mcp"},
        "tools": {"count": 2, "names": ["get_weather", "get_forecast"]},
        "pricing": {"currency": "INR", "amount": 0.0},
        "security_report": None,
        "meta": {
            "created_at": "2025-12-10T00:00:00+00:00",
            "updated_at": "2025-12-10T00:00:00+00:00",
        },
    }


@pytest.fixture
def auth_tokens(tmp_path: Path) -> dict:
    """Write a fake auth token file and return the payload."""
    payload = {
        "email": "test@example.com",
        "id_token": "fake-id-token",
        "refresh_token": "fake-refresh-token",
        "expires_in": 3600,
        "local_id": "uid-12345",
        "provider": "password",
    }
    auth_dir = tmp_path / ".superbox"
    auth_dir.mkdir()
    (auth_dir / "auth.json").write_text(json.dumps(payload))
    return payload
