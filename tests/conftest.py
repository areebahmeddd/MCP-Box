import boto3
import pytest
from moto import mock_aws

FAKE_ENV: dict[str, str] = {
    "SUPERBOX_API_URL": "http://localhost:8000/api/v1",
    "CLOUDFLARE_ACCOUNT_ID": "fake-account-id",
    "CLOUDFLARE_R2_ACCESS_KEY_ID": "testing",
    "CLOUDFLARE_R2_SECRET_ACCESS_KEY": "testing",
    "CLOUDFLARE_R2_BUCKET_NAME": "test-superbox-registry",
    "CLOUDFLARE_WORKER_URL": "https://superbox-executor.example.workers.dev",
    "FIREBASE_API_KEY": "fake-firebase-key",
    "FIREBASE_PROJECT_ID": "fake-project",
    "SONAR_TOKEN": "fake-sonar-token",
    "SONAR_ORGANIZATION": "fake-org",
    "SNYK_API_TOKEN": "fake-snyk-token",
    "GITGUARDIAN_API_KEY": "fake-gg-key",
    "RAZORPAY_KEY_ID": "fake-rzp-key",
    "RAZORPAY_KEY_SECRET": "fake-rzp-secret",
}

FAKE_ENV_CONTENT: str = "\n".join(f"{k}={v}" for k, v in FAKE_ENV.items()) + "\n"


@pytest.fixture(autouse=True)
def set_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in FAKE_ENV.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def s3_bucket():
    with mock_aws():
        import superbox.shared.s3 as s3_module

        real_s3_client = s3_module.s3_client

        def patched_s3_client():
            return boto3.client("s3", region_name="us-east-1")

        s3_module.s3_client = patched_s3_client

        client = boto3.client("s3", region_name="us-east-1")
        bucket_name = FAKE_ENV["CLOUDFLARE_R2_BUCKET_NAME"]
        client.create_bucket(Bucket=bucket_name)
        yield bucket_name

        s3_module.s3_client = real_s3_client


@pytest.fixture
def sample_server() -> dict:
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
