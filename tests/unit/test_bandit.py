import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from superbox.cli.scanners import bandit


def _make_output(issues: list, extra_metrics: dict | None = None) -> dict:
    metrics: dict = extra_metrics or {}
    for i in range(len(issues)):
        metrics.setdefault(f"file{i}.py", {"loc": 100, "nosec": 0})
    return {"results": issues, "metrics": metrics}


def _issue(severity: str = "HIGH", confidence: str = "HIGH", cwe_id: int = 78) -> dict:
    return {
        "issue_text": "Use of exec detected",
        "issue_severity": severity,
        "issue_confidence": confidence,
        "filename": "main.py",
        "line_number": 10,
        "test_id": "B102",
        "test_name": "exec_used",
        "issue_cwe": {"id": cwe_id},
    }


def _fake_run(output_file: str, data: dict, returncode: int = 0):
    def _run(cmd, **kwargs):
        with open(output_file, "w") as f:
            json.dump(data, f)
        m = MagicMock()
        m.returncode = returncode
        return m

    return _run


class TestBanditRunScan:
    def test_nonexistent_repo_path_returns_error(self) -> None:
        result = bandit.run_scan("/nonexistent/path")
        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert result["total_issues"] == 0

    def test_clean_scan_returns_success(self, tmp_path) -> None:
        output_file = str(tmp_path / "out.json")
        with (
            patch(
                "superbox.cli.scanners.bandit.subprocess.run",
                side_effect=_fake_run(output_file, _make_output([])),
            ),
            patch("superbox.cli.scanners.bandit.os.path.join", return_value=output_file),
        ):
            result = bandit.run_scan(str(tmp_path))
        assert result["success"] is True
        assert result["total_issues"] == 0
        assert result["severity_counts"] == {"high": 0, "medium": 0, "low": 0}

    def test_issues_counted_by_severity(self, tmp_path) -> None:
        issues = [_issue("HIGH"), _issue("MEDIUM"), _issue("MEDIUM"), _issue("LOW")]
        output_file = str(tmp_path / "out.json")
        with (
            patch(
                "superbox.cli.scanners.bandit.subprocess.run",
                side_effect=_fake_run(output_file, _make_output(issues), returncode=1),
            ),
            patch("superbox.cli.scanners.bandit.os.path.join", return_value=output_file),
        ):
            result = bandit.run_scan(str(tmp_path))
        assert result["success"] is False
        assert result["total_issues"] == 4
        assert result["severity_counts"] == {"high": 1, "medium": 2, "low": 1}

    def test_issues_sorted_high_to_low(self, tmp_path) -> None:
        issues = [_issue("LOW"), _issue("HIGH"), _issue("MEDIUM")]
        output_file = str(tmp_path / "out.json")
        with (
            patch(
                "superbox.cli.scanners.bandit.subprocess.run",
                side_effect=_fake_run(output_file, _make_output(issues), returncode=1),
            ),
            patch("superbox.cli.scanners.bandit.os.path.join", return_value=output_file),
        ):
            result = bandit.run_scan(str(tmp_path))
        severities = [i["severity"] for i in result["issues"]]
        assert severities == ["high", "medium", "low"]

    def test_cwe_extracted_from_dict(self, tmp_path) -> None:
        output_file = str(tmp_path / "out.json")
        with (
            patch(
                "superbox.cli.scanners.bandit.subprocess.run",
                side_effect=_fake_run(output_file, _make_output([_issue(cwe_id=79)]), returncode=1),
            ),
            patch("superbox.cli.scanners.bandit.os.path.join", return_value=output_file),
        ):
            result = bandit.run_scan(str(tmp_path))
        assert result["issues"][0]["cwe"] == 79

    def test_cwe_non_dict_returns_zero(self, tmp_path) -> None:
        issue = _issue()
        issue["issue_cwe"] = "not-a-dict"
        output_file = str(tmp_path / "out.json")
        with (
            patch(
                "superbox.cli.scanners.bandit.subprocess.run",
                side_effect=_fake_run(output_file, _make_output([issue]), returncode=1),
            ),
            patch("superbox.cli.scanners.bandit.os.path.join", return_value=output_file),
        ):
            result = bandit.run_scan(str(tmp_path))
        assert result["issues"][0]["cwe"] == 0

    def test_loc_summed_across_all_files(self, tmp_path) -> None:
        data = {
            "results": [],
            "metrics": {"a.py": {"loc": 50, "nosec": 0}, "b.py": {"loc": 75, "nosec": 0}},
        }
        output_file = str(tmp_path / "out.json")
        with (
            patch(
                "superbox.cli.scanners.bandit.subprocess.run",
                side_effect=_fake_run(output_file, data),
            ),
            patch("superbox.cli.scanners.bandit.os.path.join", return_value=output_file),
        ):
            result = bandit.run_scan(str(tmp_path))
        assert result["total_lines_scanned"] == 125

    def test_no_output_file_generated_returns_error(self, tmp_path) -> None:
        with patch(
            "superbox.cli.scanners.bandit.subprocess.run",
            return_value=MagicMock(returncode=0),
        ):
            result = bandit.run_scan(str(tmp_path))
        assert result["success"] is False

    def test_timeout_returns_error_result(self, tmp_path) -> None:
        with patch(
            "superbox.cli.scanners.bandit.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="bandit", timeout=120),
        ):
            result = bandit.run_scan(str(tmp_path))
        assert result["success"] is False
        assert "timeout" in result["error"].lower()

    def test_bandit_not_installed_raises_runtime_error(self, tmp_path) -> None:
        with patch(
            "superbox.cli.scanners.bandit.subprocess.run",
            side_effect=FileNotFoundError("bandit not found"),
        ):
            with pytest.raises(RuntimeError, match="bandit is not installed"):
                bandit.run_scan(str(tmp_path))

    def test_generic_exception_returns_error_dict(self, tmp_path) -> None:
        with patch(
            "superbox.cli.scanners.bandit.subprocess.run",
            side_effect=Exception("unexpected error"),
        ):
            result = bandit.run_scan(str(tmp_path))
        assert result["success"] is False
        assert "unexpected error" in result["error"]
