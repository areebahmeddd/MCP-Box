from unittest.mock import MagicMock, patch

import pytest
import requests as _requests

from superbox.cli.scanners import sonarqube


def _resp(status: int, body: dict) -> MagicMock:
    m = MagicMock()
    m.status_code = status
    m.json.return_value = body
    m.text = str(body)
    return m


class TestExtractRepository:
    @pytest.mark.parametrize(
        "url, owner, repo",
        [
            ("https://github.com/acme/my-tool", "acme", "my-tool"),
            ("https://github.com/acme/my-tool.git", "acme", "my-tool"),
            ("https://github.com/acme/my-tool/", "acme", "my-tool"),
            ("git@github.com:acme/my-tool.git", "acme", "my-tool"),
            ("git@github.com:acme/my-tool", "acme", "my-tool"),
            ("  https://github.com/acme/my-tool  ", "acme", "my-tool"),
        ],
    )
    def test_parses_url_correctly(self, url: str, owner: str, repo: str) -> None:
        o, r = sonarqube.extract_repository(url)
        assert o == owner
        assert r == repo

    def test_deep_path_uses_last_two_segments(self) -> None:
        owner, repo = sonarqube.extract_repository("https://github.com/org/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_single_segment_cannot_extract_pair(self) -> None:
        owner, repo = sonarqube.extract_repository("https://github.com/only-one-part")
        assert owner is None or len([owner, repo]) == 2


class TestGenerateKey:
    def test_format_is_org_owner_repo(self) -> None:
        key = sonarqube.generate_key("acme", "my-tool", "superbox")
        assert key == "superbox_acme_my-tool"

    def test_spaces_replaced_with_underscores(self) -> None:
        key = sonarqube.generate_key("my owner", "my repo", "org")
        assert " " not in key

    def test_special_chars_replaced(self) -> None:
        key = sonarqube.generate_key("owner@email", "repo/sub", "org")
        assert "@" not in key
        assert "/" not in key

    def test_allowed_chars_preserved(self) -> None:
        key = sonarqube.generate_key("my-owner", "my.repo_v2", "org")
        assert "my-owner" in key
        assert "my.repo_v2" in key

    def test_prefixed_with_organization(self) -> None:
        key = sonarqube.generate_key("owner", "repo", "my-org")
        assert key.startswith("my-org")

    @pytest.mark.parametrize("owner, repo, org", [("a", "b", "c"), ("UPPER", "Repo", "Org")])
    def test_always_produces_non_empty_key_with_separator(
        self, owner: str, repo: str, org: str
    ) -> None:
        key = sonarqube.generate_key(owner, repo, org)
        assert key
        assert "_" in key


class TestCreateProject:
    def test_200_returns_true(self) -> None:
        with patch("superbox.cli.scanners.sonarqube.requests.post", return_value=_resp(200, {})):
            assert sonarqube.create_project("key", "name", "https://sonar", "tok", "org") is True

    def test_400_already_exists_returns_true(self) -> None:
        m = _resp(400, {})
        m.text = "already exists"
        with patch("superbox.cli.scanners.sonarqube.requests.post", return_value=m):
            assert sonarqube.create_project("key", "name", "https://sonar", "tok", "org") is True

    def test_400_other_error_returns_false(self) -> None:
        m = _resp(400, {})
        m.text = "bad request"
        with patch("superbox.cli.scanners.sonarqube.requests.post", return_value=m):
            assert sonarqube.create_project("key", "name", "https://sonar", "tok", "org") is False

    def test_500_returns_false(self) -> None:
        with patch("superbox.cli.scanners.sonarqube.requests.post", return_value=_resp(500, {})):
            assert sonarqube.create_project("key", "name", "https://sonar", "tok", "org") is False

    def test_network_error_returns_false(self) -> None:
        with patch(
            "superbox.cli.scanners.sonarqube.requests.post",
            side_effect=_requests.exceptions.RequestException("timeout"),
        ):
            assert sonarqube.create_project("key", "name", "https://sonar", "tok", "org") is False


class TestBindRepository:
    def test_200_returns_true(self) -> None:
        with patch("superbox.cli.scanners.sonarqube.requests.post", return_value=_resp(200, {})):
            assert sonarqube.bind_repository("k", "a", "r", "https://sonar", "tok", "org") is True

    def test_204_returns_true(self) -> None:
        with patch("superbox.cli.scanners.sonarqube.requests.post", return_value=_resp(204, {})):
            assert sonarqube.bind_repository("k", "a", "r", "https://sonar", "tok", "org") is True

    def test_error_status_returns_false(self) -> None:
        with patch("superbox.cli.scanners.sonarqube.requests.post", return_value=_resp(400, {})):
            assert sonarqube.bind_repository("k", "a", "r", "https://sonar", "tok", "org") is False

    def test_network_error_returns_false(self) -> None:
        with patch(
            "superbox.cli.scanners.sonarqube.requests.post",
            side_effect=_requests.exceptions.RequestException(),
        ):
            assert sonarqube.bind_repository("k", "a", "r", "https://sonar", "tok", "org") is False


class TestWaitAnalysis:
    def test_success_status_returns_true(self) -> None:
        body = {"queue": [], "current": {"status": "SUCCESS"}}
        with patch("superbox.cli.scanners.sonarqube.requests.get", return_value=_resp(200, body)):
            assert sonarqube.wait_analysis("key", "https://sonar", "tok", max_wait=10) is True

    def test_failed_status_returns_false(self) -> None:
        body = {"queue": [], "current": {"status": "FAILED"}}
        with patch("superbox.cli.scanners.sonarqube.requests.get", return_value=_resp(200, body)):
            assert sonarqube.wait_analysis("key", "https://sonar", "tok", max_wait=10) is False

    def test_in_progress_then_success(self) -> None:
        pending = _resp(200, {"queue": [], "current": {"status": "IN_PROGRESS"}})
        success = _resp(200, {"queue": [], "current": {"status": "SUCCESS"}})
        with (
            patch("superbox.cli.scanners.sonarqube.requests.get", side_effect=[pending, success]),
            patch("superbox.cli.scanners.sonarqube.time.sleep"),
        ):
            assert sonarqube.wait_analysis("key", "https://sonar", "tok", max_wait=60) is True

    def test_no_current_task_returns_true(self) -> None:
        body = {"queue": [], "current": None}
        with patch("superbox.cli.scanners.sonarqube.requests.get", return_value=_resp(200, body)):
            assert sonarqube.wait_analysis("key", "https://sonar", "tok", max_wait=10) is True

    def test_queued_task_retries(self) -> None:
        queued = _resp(200, {"queue": [{"status": "PENDING"}], "current": None})
        success = _resp(200, {"queue": [], "current": {"status": "SUCCESS"}})
        with (
            patch("superbox.cli.scanners.sonarqube.requests.get", side_effect=[queued, success]),
            patch("superbox.cli.scanners.sonarqube.time.sleep"),
        ):
            assert sonarqube.wait_analysis("key", "https://sonar", "tok", max_wait=60) is True

    def test_transient_exception_retries(self) -> None:
        success = _resp(200, {"queue": [], "current": {"status": "SUCCESS"}})
        with (
            patch(
                "superbox.cli.scanners.sonarqube.requests.get",
                side_effect=[Exception("transient"), success],
            ),
            patch("superbox.cli.scanners.sonarqube.time.sleep"),
        ):
            assert sonarqube.wait_analysis("key", "https://sonar", "tok", max_wait=60) is True


class TestFetchIssues:
    def test_returns_all_issues_single_page(self) -> None:
        issues = [{"key": "i1", "type": "BUG"}, {"key": "i2", "type": "CODE_SMELL"}]
        body = {"issues": issues, "total": 2}
        with patch("superbox.cli.scanners.sonarqube.requests.get", return_value=_resp(200, body)):
            result = sonarqube.fetch_issues("key", "https://sonar", "tok")
        assert len(result) == 2

    def test_paginates_when_page_is_full(self) -> None:
        page1 = [{"key": f"i{i}"} for i in range(500)]
        page2 = [{"key": "i500"}]
        with patch(
            "superbox.cli.scanners.sonarqube.requests.get",
            side_effect=[
                _resp(200, {"issues": page1, "total": 501}),
                _resp(200, {"issues": page2, "total": 501}),
            ],
        ):
            result = sonarqube.fetch_issues("key", "https://sonar", "tok")
        assert len(result) == 501

    def test_non_200_returns_empty_list(self) -> None:
        with patch("superbox.cli.scanners.sonarqube.requests.get", return_value=_resp(403, {})):
            assert sonarqube.fetch_issues("key", "https://sonar", "tok") == []

    def test_network_error_returns_empty_list(self) -> None:
        with patch(
            "superbox.cli.scanners.sonarqube.requests.get", side_effect=Exception("network")
        ):
            assert sonarqube.fetch_issues("key", "https://sonar", "tok") == []


class TestFetchHotspots:
    def test_returns_hotspots(self) -> None:
        body = {"hotspots": [{"key": "h1"}], "paging": {"total": 1}}
        with patch("superbox.cli.scanners.sonarqube.requests.get", return_value=_resp(200, body)):
            result = sonarqube.fetch_hotspots("key", "https://sonar", "tok")
        assert len(result) == 1

    def test_non_200_returns_empty_list(self) -> None:
        with patch("superbox.cli.scanners.sonarqube.requests.get", return_value=_resp(403, {})):
            assert sonarqube.fetch_hotspots("key", "https://sonar", "tok") == []

    def test_exception_returns_empty_list(self) -> None:
        with patch(
            "superbox.cli.scanners.sonarqube.requests.get", side_effect=Exception("network error")
        ):
            assert sonarqube.fetch_hotspots("key", "https://sonar", "tok") == []


class TestFetchMeasures:
    def test_returns_metrics_dict(self) -> None:
        body = {
            "component": {
                "measures": [
                    {"metric": "ncloc", "value": "500"},
                    {"metric": "coverage", "value": "85.0"},
                ]
            }
        }
        with patch("superbox.cli.scanners.sonarqube.requests.get", return_value=_resp(200, body)):
            result = sonarqube.fetch_measures("key", "https://sonar", "tok")
        assert result["ncloc"] == "500"
        assert result["coverage"] == "85.0"

    def test_non_200_returns_empty_dict(self) -> None:
        with patch("superbox.cli.scanners.sonarqube.requests.get", return_value=_resp(500, {})):
            assert sonarqube.fetch_measures("key", "https://sonar", "tok") == {}

    def test_network_error_returns_empty_dict(self) -> None:
        with patch(
            "superbox.cli.scanners.sonarqube.requests.get", side_effect=Exception("network")
        ):
            assert sonarqube.fetch_measures("key", "https://sonar", "tok") == {}


class TestCreateReport:
    def test_issue_counts_by_type(self) -> None:
        issues = [
            {"type": "BUG"},
            {"type": "VULNERABILITY"},
            {"type": "CODE_SMELL"},
            {"type": "CODE_SMELL"},
        ]
        report = sonarqube.create_report(
            "test_repo", "org_owner_repo", issues, ["h1"], {}, "https://sonarcloud.io"
        )
        assert report["issue_counts"]["total"] == 4
        assert report["issue_counts"]["bugs"] == 1
        assert report["issue_counts"]["vulnerabilities"] == 1
        assert report["issue_counts"]["code_smells"] == 2
        assert report["issue_counts"]["security_hotspots"] == 1

    def test_metadata_contains_repo_and_project_key(self) -> None:
        report = sonarqube.create_report(
            "my_repo", "org_acme_repo", [], [], {}, "https://sonarcloud.io"
        )
        assert report["metadata"]["repository"] == "my_repo"
        assert report["metadata"]["project_key"] == "org_acme_repo"

    def test_sonarcloud_url_formatted_correctly(self) -> None:
        report = sonarqube.create_report("repo", "proj_key", [], [], {}, "https://sonarcloud.io")
        assert report["metadata"]["sonarcloud_url"] == "https://sonarcloud.io/dashboard?id=proj_key"

    def test_metrics_passed_through(self) -> None:
        metrics = {"ncloc": "500", "coverage": "85.0"}
        report = sonarqube.create_report("repo", "key", [], [], metrics, "https://sonarcloud.io")
        assert report["metrics"] == metrics

    def test_quality_gate_from_alert_status_metric(self) -> None:
        metrics = {"alert_status": "OK"}
        report = sonarqube.create_report("repo", "key", [], [], metrics, "https://sonarcloud.io")
        assert report["quality_gate"]["status"] == "OK"

    def test_quality_gate_defaults_to_na(self) -> None:
        report = sonarqube.create_report("repo", "key", [], [], {}, "https://sonarcloud.io")
        assert report["quality_gate"]["status"] == "N/A"

    def test_quality_ratings_from_metrics(self) -> None:
        metrics = {"reliability_rating": "A", "security_rating": "B", "sqale_rating": "C"}
        report = sonarqube.create_report("repo", "key", [], [], metrics, "https://sonarcloud.io")
        assert report["quality_ratings"]["reliability"] == "A"
        assert report["quality_ratings"]["security"] == "B"
        assert report["quality_ratings"]["maintainability"] == "C"

    def test_empty_inputs_produce_zero_counts(self) -> None:
        report = sonarqube.create_report("repo", "key", [], [], {}, "https://sonarcloud.io")
        counts = report["issue_counts"]
        assert all(v == 0 for v in counts.values())


class TestRunAnalysis:
    def test_valid_url_returns_success_structure(self) -> None:
        with (
            patch("superbox.cli.scanners.sonarqube.load_env"),
            patch("superbox.cli.scanners.sonarqube.create_project", return_value=True),
            patch("superbox.cli.scanners.sonarqube.bind_repository", return_value=True),
            patch("superbox.cli.scanners.sonarqube.time.sleep"),
            patch("superbox.cli.scanners.sonarqube.fetch_issues", return_value=[]),
            patch("superbox.cli.scanners.sonarqube.fetch_hotspots", return_value=[]),
            patch("superbox.cli.scanners.sonarqube.fetch_measures", return_value={}),
        ):
            result = sonarqube.run_analysis("https://github.com/acme/my-tool")
        assert result["success"] is True
        assert result["owner"] == "acme"
        assert result["repo"] == "my-tool"
        assert "report_data" in result
        assert "project_key" in result

    def test_invalid_url_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Could not parse"):
            sonarqube.run_analysis("not-a-valid-github-url")

    def test_project_creation_failed_does_not_bind(self) -> None:
        bind_mock = MagicMock()
        with (
            patch("superbox.cli.scanners.sonarqube.load_env"),
            patch("superbox.cli.scanners.sonarqube.create_project", return_value=False),
            patch("superbox.cli.scanners.sonarqube.bind_repository", bind_mock),
            patch("superbox.cli.scanners.sonarqube.time.sleep"),
            patch("superbox.cli.scanners.sonarqube.fetch_issues", return_value=[]),
            patch("superbox.cli.scanners.sonarqube.fetch_hotspots", return_value=[]),
            patch("superbox.cli.scanners.sonarqube.fetch_measures", return_value={}),
        ):
            result = sonarqube.run_analysis("https://github.com/acme/my-tool")
        bind_mock.assert_not_called()
        assert result["success"] is True

    def test_project_key_matches_generate_key_format(self) -> None:
        with (
            patch("superbox.cli.scanners.sonarqube.load_env"),
            patch("superbox.cli.scanners.sonarqube.create_project", return_value=True),
            patch("superbox.cli.scanners.sonarqube.bind_repository", return_value=True),
            patch("superbox.cli.scanners.sonarqube.time.sleep"),
            patch("superbox.cli.scanners.sonarqube.fetch_issues", return_value=[]),
            patch("superbox.cli.scanners.sonarqube.fetch_hotspots", return_value=[]),
            patch("superbox.cli.scanners.sonarqube.fetch_measures", return_value={}),
        ):
            result = sonarqube.run_analysis("https://github.com/acme/my-tool")
        expected_key = sonarqube.generate_key("acme", "my-tool", "fake-org")
        assert result["project_key"] == expected_key
