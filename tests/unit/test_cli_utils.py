from unittest.mock import patch

import pytest

from superbox.cli.utils import build_report, config_path, show_summary


def _sonar(total: int = 0, bugs: int = 0, vulns: int = 0, coverage: float = 100.0) -> dict:
    return {
        "issue_counts": {
            "total": total,
            "bugs": bugs,
            "vulnerabilities": vulns,
            "code_smells": 0,
            "security_hotspots": 0,
        },
        "quality_gate": {"status": "OK"},
        "quality_ratings": {"reliability": "A", "security": "A", "maintainability": "A"},
        "metrics": {"coverage": coverage, "duplicated_lines_density": 0, "ncloc": 100},
        "metadata": {"sonarcloud_url": "https://sonarcloud.io/project"},
    }


def _snyk(vulns: int = 0, critical: int = 0, high: int = 0) -> dict:
    return {
        "success": vulns == 0,
        "total_vulnerabilities": vulns,
        "severity_counts": {"critical": critical, "high": high, "medium": 0, "low": 0},
        "vulnerabilities": [],
    }


def _gg(secrets: int = 0) -> dict:
    return {"success": secrets == 0, "total_secrets": secrets, "secrets": []}


def _bandit(issues: int = 0, high: int = 0) -> dict:
    return {
        "success": issues == 0,
        "total_issues": issues,
        "severity_counts": {"high": high, "medium": 0, "low": 0},
        "total_lines_scanned": 200,
        "issues": [],
    }


class TestBuildReport:
    def test_clean_scan_passes(self) -> None:
        report = build_report("repo", "https://github.com/a/b", _sonar(), _snyk(), _gg(), _bandit())
        assert report["summary"]["scan_passed"] is True
        assert report["summary"]["total_issues_all_scanners"] == 0
        assert report["recommendations"] == ["All security scans passed"]

    def test_total_issues_sums_all_scanners(self) -> None:
        report = build_report(
            "repo", "url", _sonar(total=2), _snyk(vulns=1), _gg(secrets=1), _bandit(issues=3)
        )
        assert report["summary"]["total_issues_all_scanners"] == 7
        assert report["summary"]["scan_passed"] is False

    def test_secrets_adds_rotate_recommendation(self) -> None:
        report = build_report("repo", "url", _sonar(), _snyk(), _gg(secrets=1), _bandit())
        recs = report["recommendations"]
        assert any("rotate" in r.lower() for r in recs)

    def test_critical_snyk_adds_update_recommendation(self) -> None:
        report = build_report("repo", "url", _sonar(), _snyk(vulns=1, critical=1), _gg(), _bandit())
        recs = report["recommendations"]
        assert any("update" in r.lower() or "dependency" in r.lower() for r in recs)

    def test_high_severity_bandit_adds_recommendation(self) -> None:
        report = build_report("repo", "url", _sonar(), _snyk(), _gg(), _bandit(issues=1, high=1))
        recs = report["recommendations"]
        assert any("high" in r.lower() or "security" in r.lower() for r in recs)

    def test_low_coverage_adds_recommendation(self) -> None:
        report = build_report("repo", "url", _sonar(coverage=50.0), _snyk(), _gg(), _bandit())
        recs = report["recommendations"]
        assert any("coverage" in r.lower() or "test" in r.lower() for r in recs)

    def test_report_contains_expected_scanner_sections(self) -> None:
        report = build_report("repo", "url", _sonar(), _snyk(), _gg(), _bandit())
        assert "sonarqube" in report
        assert "snyk" in report
        assert "gitguardian" in report
        assert "bandit" in report
        assert "metadata" in report

    def test_metadata_captures_repo_url(self) -> None:
        report = build_report(
            "my-repo", "https://github.com/me/my-repo", _sonar(), _snyk(), _gg(), _bandit()
        )
        assert report["metadata"]["repo_url"] == "https://github.com/me/my-repo"
        assert report["metadata"]["repository"] == "my-repo"


class TestShowSummary:
    def test_no_issues_outputs_passed(self, capsys) -> None:
        report = build_report("r", "url", _sonar(), _snyk(), _gg(), _bandit())
        show_summary(report)
        out = capsys.readouterr().out
        assert "passed" in out.lower() or "no issues" in out.lower()

    def test_issues_outputs_count(self, capsys) -> None:
        report = build_report("r", "url", _sonar(total=3), _snyk(), _gg(), _bandit())
        show_summary(report)
        out = capsys.readouterr().out
        assert "3" in out


class TestConfigPath:
    @pytest.mark.parametrize(
        "app,expected_fragment",
        [
            ("vscode", "Code"),
            ("cursor", ".cursor"),
            ("windsurf", "Windsurf"),
            ("claude", "Claude"),
            ("chatgpt", "ChatGPT"),
        ],
    )
    def test_windows_paths(self, app: str, expected_fragment: str, monkeypatch) -> None:
        monkeypatch.setenv("APPDATA", r"C:\Users\Test\AppData\Roaming")
        monkeypatch.setenv("USERPROFILE", r"C:\Users\Test")
        with patch("platform.system", return_value="Windows"):
            path = config_path(app)
            assert expected_fragment in str(path)
            assert path.name.endswith(".json")

    def test_unsupported_app_raises(self) -> None:
        with pytest.raises((RuntimeError, Exception)):
            config_path("unknown-app")
