from unittest.mock import MagicMock, patch

import requests as _requests

from superbox.cli.scanners import snyk


def _resp(status: int, body: dict) -> MagicMock:
    m = MagicMock()
    m.status_code = status
    m.json.return_value = body
    return m


def _vuln(severity: str = "high", pkg: str = "requests") -> dict:
    return {
        "id": "SNYK-PYTHON-001",
        "title": "Remote Code Execution",
        "packageName": pkg,
        "version": "2.0.0",
        "severity": severity,
        "identifiers": {"CVE": ["CVE-2023-9999"]},
        "cvssScore": 9.8,
        "isUpgradable": True,
        "isPatchable": False,
    }


class TestSnykRunScan:
    def test_nonexistent_repo_path_returns_error(self) -> None:
        result = snyk.run_scan("/nonexistent/path")
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_no_requirements_txt_skips_scan(self, tmp_path) -> None:
        result = snyk.run_scan(str(tmp_path))
        assert result["success"] is True
        assert result["total_vulnerabilities"] == 0

    def test_clean_scan_returns_success(self, tmp_path) -> None:
        (tmp_path / "requirements.txt").write_text("requests==2.32.0\n")
        with patch(
            "superbox.cli.scanners.snyk.requests.post",
            return_value=_resp(200, {"issues": {"vulnerabilities": []}}),
        ):
            result = snyk.run_scan(str(tmp_path))
        assert result["success"] is True
        assert result["total_vulnerabilities"] == 0

    def test_vulnerabilities_counted_by_severity(self, tmp_path) -> None:
        (tmp_path / "requirements.txt").write_text("requests==2.0.0\n")
        vulns = [_vuln("critical"), _vuln("high"), _vuln("medium"), _vuln("low")]
        with patch(
            "superbox.cli.scanners.snyk.requests.post",
            return_value=_resp(200, {"issues": {"vulnerabilities": vulns}}),
        ):
            result = snyk.run_scan(str(tmp_path))
        assert result["success"] is False
        assert result["total_vulnerabilities"] == 4
        assert result["severity_counts"]["critical"] == 1
        assert result["severity_counts"]["high"] == 1
        assert result["severity_counts"]["medium"] == 1
        assert result["severity_counts"]["low"] == 1

    def test_vulnerabilities_sorted_critical_first(self, tmp_path) -> None:
        (tmp_path / "requirements.txt").write_text("requests==2.0.0\n")
        vulns = [_vuln("low"), _vuln("critical"), _vuln("medium")]
        with patch(
            "superbox.cli.scanners.snyk.requests.post",
            return_value=_resp(200, {"issues": {"vulnerabilities": vulns}}),
        ):
            result = snyk.run_scan(str(tmp_path))
        severities = [v["severity"] for v in result["vulnerabilities"]]
        assert severities == ["critical", "medium", "low"]

    def test_401_returns_invalid_token_error(self, tmp_path) -> None:
        (tmp_path / "requirements.txt").write_text("requests==2.0.0\n")
        with patch("superbox.cli.scanners.snyk.requests.post", return_value=_resp(401, {})):
            result = snyk.run_scan(str(tmp_path))
        assert result["success"] is False
        assert "token" in result["error"].lower()

    def test_404_returns_not_found_error(self, tmp_path) -> None:
        (tmp_path / "requirements.txt").write_text("requests==2.0.0\n")
        with patch("superbox.cli.scanners.snyk.requests.post", return_value=_resp(404, {})):
            result = snyk.run_scan(str(tmp_path))
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_other_non_200_returns_status_error(self, tmp_path) -> None:
        (tmp_path / "requirements.txt").write_text("requests==2.0.0\n")
        with patch("superbox.cli.scanners.snyk.requests.post", return_value=_resp(500, {})):
            result = snyk.run_scan(str(tmp_path))
        assert result["success"] is False
        assert "500" in result["error"]

    def test_network_error_returns_error(self, tmp_path) -> None:
        (tmp_path / "requirements.txt").write_text("requests==2.0.0\n")
        with patch(
            "superbox.cli.scanners.snyk.requests.post",
            side_effect=_requests.RequestException("connection refused"),
        ):
            result = snyk.run_scan(str(tmp_path))
        assert result["success"] is False
        assert "api request failed" in result["error"].lower()

    def test_cve_string_wrapped_in_list(self, tmp_path) -> None:
        (tmp_path / "requirements.txt").write_text("requests==2.0.0\n")
        vuln = _vuln()
        vuln["identifiers"]["CVE"] = "CVE-2023-0001"
        with patch(
            "superbox.cli.scanners.snyk.requests.post",
            return_value=_resp(200, {"issues": {"vulnerabilities": [vuln]}}),
        ):
            result = snyk.run_scan(str(tmp_path))
        assert result["vulnerabilities"][0]["cve"] == ["CVE-2023-0001"]

    def test_500_with_message_includes_message_in_error(self, tmp_path) -> None:
        (tmp_path / "requirements.txt").write_text("requests==2.0.0\n")
        with patch(
            "superbox.cli.scanners.snyk.requests.post",
            return_value=_resp(500, {"message": "internal server error"}),
        ):
            result = snyk.run_scan(str(tmp_path))
        assert "500" in result["error"]
