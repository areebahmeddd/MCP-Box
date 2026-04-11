import boto3
import pytest
from freezegun import freeze_time
from unittest.mock import MagicMock, patch

from superbox.shared import s3


@pytest.fixture(autouse=True)
def _aws(s3_bucket):
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

    def test_key_is_name_dot_json(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "my-server", sample_server)
        client = boto3.client("s3", region_name="us-east-1")
        keys = [obj["Key"] for obj in client.list_objects_v2(Bucket=BUCKET)["Contents"]]
        assert "my-server.json" in keys


class TestSaveServer:
    def test_round_trip_preserves_data(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "weather-mcp", sample_server)
        fetched = s3.get_server(BUCKET, "weather-mcp")
        assert fetched["description"] == sample_server["description"]
        assert fetched["repository"]["url"] == sample_server["repository"]["url"]

    def test_name_auto_added_when_missing(self) -> None:
        data = {"version": "1.0.0", "description": "no name key"}
        s3.save_server(BUCKET, "auto-name", data)
        fetched = s3.get_server(BUCKET, "auto-name")
        assert fetched["name"] == "auto-name"

    def test_existing_name_not_overwritten_by_auto_add(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "weather-mcp", sample_server)
        fetched = s3.get_server(BUCKET, "weather-mcp")
        assert fetched["name"] == "weather-mcp"

    def test_overwrites_existing_entry(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "weather-mcp", sample_server)
        updated = dict(sample_server, description="Updated description")
        s3.save_server(BUCKET, "weather-mcp", updated)
        fetched = s3.get_server(BUCKET, "weather-mcp")
        assert fetched["description"] == "Updated description"

    def test_returns_true_on_success(self, sample_server: dict) -> None:
        result = s3.save_server(BUCKET, "weather-mcp", sample_server)
        assert result is True


class TestListServers:
    def test_returns_all_saved_servers(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "alpha", sample_server)
        s3.save_server(BUCKET, "beta", dict(sample_server, name="beta"))
        servers = s3.list_servers(BUCKET)
        assert "alpha" in servers
        assert "beta" in servers

    def test_returns_empty_dict_when_no_servers(self) -> None:
        assert s3.list_servers(BUCKET) == {}

    def test_ignores_non_json_objects(self) -> None:
        client = boto3.client("s3", region_name="us-east-1")
        client.put_object(Bucket=BUCKET, Key="README.md", Body=b"# readme")
        servers = s3.list_servers(BUCKET)
        assert "README" not in servers

    def test_skips_corrupt_json_entries(self) -> None:
        client = boto3.client("s3", region_name="us-east-1")
        client.put_object(Bucket=BUCKET, Key="good.json", Body=b'{"name":"good"}')
        client.put_object(Bucket=BUCKET, Key="bad.json", Body=b"NOT_JSON")
        servers = s3.list_servers(BUCKET)
        assert "good" in servers
        assert "bad" not in servers

    def test_handles_pagination_with_continuation_token(self) -> None:
        mock_client = MagicMock()
        page1 = {
            "Contents": [{"Key": "srv1.json"}],
            "IsTruncated": True,
            "NextContinuationToken": "tok-abc",
        }
        page2 = {"Contents": [{"Key": "srv2.json"}], "IsTruncated": False}
        mock_client.list_objects_v2.side_effect = [page1, page2]
        mock_client.get_object.side_effect = [
            {"Body": MagicMock(read=lambda: b'{"name": "srv1"}')},
            {"Body": MagicMock(read=lambda: b'{"name": "srv2"}')},
        ]
        with patch("superbox.shared.s3.s3_client", return_value=mock_client):
            result = s3.list_servers("test-bucket")
        assert "srv1" in result
        assert "srv2" in result
        second_call = mock_client.list_objects_v2.call_args_list[1][1]
        assert second_call["ContinuationToken"] == "tok-abc"

    def test_get_server_exception_in_loop_is_skipped(self) -> None:
        mock_client = MagicMock()
        mock_client.list_objects_v2.return_value = {
            "Contents": [{"Key": "boom.json"}],
            "IsTruncated": False,
        }
        mock_client.get_object.side_effect = Exception("unexpected S3 error")
        with patch("superbox.shared.s3.s3_client", return_value=mock_client):
            result = s3.list_servers("test-bucket")
        assert result == {}


class TestCheckServer:
    def test_returns_true_and_data_when_exists(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "weather-mcp", sample_server)
        exists, data = s3.check_server(BUCKET, "weather-mcp")
        assert exists is True
        assert data["name"] == "weather-mcp"

    def test_returns_false_and_empty_dict_when_missing(self) -> None:
        exists, data = s3.check_server(BUCKET, "ghost")
        assert exists is False
        assert data == {}


class TestUpsertServer:
    @freeze_time("2025-12-10T12:00:00+00:00")
    def test_new_server_gets_timestamps(self, sample_server: dict) -> None:
        payload = dict(sample_server)
        payload.pop("meta", None)
        s3.upsert_server(BUCKET, "new-server", payload)
        result = s3.get_server(BUCKET, "new-server")
        assert result["meta"]["created_at"] == "2025-12-10T12:00:00+00:00"
        assert result["meta"]["updated_at"] == "2025-12-10T12:00:00+00:00"

    @freeze_time("2025-12-10T12:00:00+00:00")
    def test_update_preserves_created_at(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "weather-mcp", sample_server)
        original_created = sample_server["meta"]["created_at"]

        updated = dict(sample_server, description="new desc")
        s3.upsert_server(BUCKET, "weather-mcp", updated)

        result = s3.get_server(BUCKET, "weather-mcp")
        assert result["meta"]["created_at"] == original_created
        assert result["meta"]["updated_at"] == "2025-12-10T12:00:00+00:00"

    @freeze_time("2025-12-10T12:00:00+00:00")
    def test_meta_with_no_created_at_gets_one_set(self, sample_server: dict) -> None:
        payload = dict(sample_server)
        payload["meta"] = {}
        s3.upsert_server(BUCKET, "new-server", payload)
        result = s3.get_server(BUCKET, "new-server")
        assert result["meta"]["created_at"] == "2025-12-10T12:00:00+00:00"

    def test_returns_true_on_success(self, sample_server: dict) -> None:
        result = s3.upsert_server(BUCKET, "weather-mcp", sample_server)
        assert result is True


class TestDeleteServer:
    def test_deletes_existing_server(self, sample_server: dict) -> None:
        s3.save_server(BUCKET, "weather-mcp", sample_server)
        s3.delete_server(BUCKET, "weather-mcp")
        assert s3.get_server(BUCKET, "weather-mcp") is None

    def test_delete_nonexistent_returns_true(self) -> None:
        result = s3.delete_server(BUCKET, "nonexistent")
        assert result is True

    def test_exception_on_delete_returns_false(self) -> None:
        mock_client = MagicMock()
        mock_client.delete_object.side_effect = Exception("S3 error")
        with patch("superbox.shared.s3.s3_client", return_value=mock_client):
            result = s3.delete_server(BUCKET, "some-server")
        assert result is False
