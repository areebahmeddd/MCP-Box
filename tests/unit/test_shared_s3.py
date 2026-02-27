import boto3
import pytest
from freezegun import freeze_time

from superbox.shared import s3


@pytest.fixture(autouse=True)
def _aws(s3_bucket):
    """Activate moto S3 mock for every test in this module."""
    yield


BUCKET = "test-superbox-registry"


class TestGetServer:
    def test_returns_data_when_found(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "weather-mcp", sample_server)
        result = s3.get_server(BUCKET, "weather-mcp")
        assert result is not None
        assert result["name"] == "weather-mcp"

    def test_returns_none_when_missing(self) -> None:
        assert s3.get_server(BUCKET, "does-not-exist") is None


class TestSaveServer:
    def test_round_trip(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "weather-mcp", sample_server)
        fetched = s3.get_server(BUCKET, "weather-mcp")
        assert fetched["description"] == sample_server["description"]
        assert fetched["repository"]["url"] == sample_server["repository"]["url"]

    def test_overwrites_existing(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "weather-mcp", sample_server)
        updated = dict(sample_server, description="Updated description")
        s3.save_server(BUCKET, "weather-mcp", updated)
        fetched = s3.get_server(BUCKET, "weather-mcp")
        assert fetched["description"] == "Updated description"


class TestListServers:
    def test_returns_all_servers(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "alpha", sample_server)
        s3.save_server(BUCKET, "beta", dict(sample_server, name="beta"))
        servers = s3.list_servers(BUCKET)
        assert "alpha" in servers
        assert "beta" in servers

    def test_returns_empty_dict_when_no_servers(self) -> None:
        assert s3.list_servers(BUCKET) == {}

    def test_ignores_non_json_objects(self) -> None:
        """put_object with a non-.json key should not appear in list."""
        client = boto3.client("s3", region_name="ap-south-1")
        client.put_object(Bucket=BUCKET, Key="README.md", Body=b"# readme")
        servers = s3.list_servers(BUCKET)
        assert "README" not in servers


class TestCheckServer:
    def test_returns_true_and_data_when_exists(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "weather-mcp", sample_server)
        exists, data = s3.check_server(BUCKET, "weather-mcp")
        assert exists is True
        assert data["name"] == "weather-mcp"

    def test_returns_false_and_empty_when_missing(self) -> None:
        exists, data = s3.check_server(BUCKET, "ghost")
        assert exists is False
        assert data == {}


class TestUpsertServer:
    @freeze_time("2025-12-10T12:00:00+00:00")
    def test_creates_with_timestamps(self, sample_server: dict) -> None:
        payload = dict(sample_server)
        payload.pop("meta", None)
        s3.upsert_server(BUCKET, "new-server", payload)
        result = s3.get_server(BUCKET, "new-server")
        assert result["meta"]["created_at"] == "2025-12-10T12:00:00+00:00"
        assert result["meta"]["updated_at"] == "2025-12-10T12:00:00+00:00"

    @freeze_time("2025-12-10T12:00:00+00:00")
    def test_preserves_created_at_on_update(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "weather-mcp", sample_server)
        original_created = sample_server["meta"]["created_at"]

        updated = dict(sample_server, description="new desc")
        s3.upsert_server(BUCKET, "weather-mcp", updated)

        result = s3.get_server(BUCKET, "weather-mcp")
        assert result["meta"]["created_at"] == original_created
        assert result["meta"]["updated_at"] == "2025-12-10T12:00:00+00:00"


class TestDeleteServer:
    def test_deletes_existing_server(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "weather-mcp", sample_server)
        s3.delete_server(BUCKET, "weather-mcp")
        assert s3.get_server(BUCKET, "weather-mcp") is None

    def test_delete_nonexistent_returns_true(self) -> None:
        """delete_server swallows exceptions — should not raise."""
        result = s3.delete_server(BUCKET, "nonexistent")
        assert result is True
