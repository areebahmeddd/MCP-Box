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
    def test_clean_scan_passes_and_recommends_all_passed(self) -> None:
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

    def test_secrets_triggers_rotate_recommendation(self) -> None:
        report = build_report("repo", "url", _sonar(), _snyk(), _gg(secrets=1), _bandit())
        assert any("rotate" in r.lower() for r in report["recommendations"])

    def test_critical_snyk_triggers_update_recommendation(self) -> None:
        report = build_report("repo", "url", _sonar(), _snyk(vulns=1, critical=1), _gg(), _bandit())
        assert any(
            "update" in r.lower() or "dependency" in r.lower() for r in report["recommendations"]
        )

    def test_high_snyk_triggers_dependency_recommendation(self) -> None:
        report = build_report("repo", "url", _sonar(), _snyk(vulns=1, high=1), _gg(), _bandit())
        assert any(
            "dependency" in r.lower() or "update" in r.lower() for r in report["recommendations"]
        )

    def test_high_bandit_triggers_high_severity_recommendation(self) -> None:
        report = build_report("repo", "url", _sonar(), _snyk(), _gg(), _bandit(issues=1, high=1))
        assert any("high" in r.lower() for r in report["recommendations"])

    def test_bandit_issues_triggers_security_recommendation(self) -> None:
        report = build_report("repo", "url", _sonar(), _snyk(), _gg(), _bandit(issues=2))
        assert any(
            "security" in r.lower() or "vulnerabilit" in r.lower()
            for r in report["recommendations"]
        )

    def test_coverage_below_80_triggers_test_recommendation(self) -> None:
        report = build_report("repo", "url", _sonar(coverage=50.0), _snyk(), _gg(), _bandit())
        assert any(
            "coverage" in r.lower() or "test" in r.lower() for r in report["recommendations"]
        )

    def test_sonar_issues_over_five_triggers_critical_recommendation(self) -> None:
        report = build_report("repo", "url", _sonar(total=6), _snyk(), _gg(), _bandit())
        assert any(
            "critical" in r.lower() or "immediate" in r.lower() for r in report["recommendations"]
        )

    def test_report_contains_all_scanner_sections(self) -> None:
        report = build_report("repo", "url", _sonar(), _snyk(), _gg(), _bandit())
        assert "sonarqube" in report
        assert "snyk" in report
        assert "gitguardian" in report
        assert "bandit" in report
        assert "metadata" in report
        assert "summary" in report
        assert "recommendations" in report

    def test_metadata_captures_repo_name_and_url(self) -> None:
        report = build_report(
            "my-repo", "https://github.com/me/my-repo", _sonar(), _snyk(), _gg(), _bandit()
        )
        assert report["metadata"]["repo_url"] == "https://github.com/me/my-repo"
        assert report["metadata"]["repository"] == "my-repo"

    def test_sonarqube_section_maps_correctly(self) -> None:
        report = build_report("r", "u", _sonar(total=3, bugs=1, vulns=2), _snyk(), _gg(), _bandit())
        sq = report["sonarqube"]
        assert sq["total_issues"] == 3
        assert sq["bugs"] == 1
        assert sq["vulnerabilities"] == 2

    def test_coverage_string_value_handled(self) -> None:
        sonar = _sonar()
        sonar["metrics"]["coverage"] = "75.0"
        report = build_report("r", "u", sonar, _snyk(), _gg(), _bandit())
        assert any("coverage" in r.lower() for r in report["recommendations"])

    def test_coverage_invalid_value_treated_as_zero(self) -> None:
        sonar = _sonar()
        sonar["metrics"]["coverage"] = "N/A"
        report = build_report("r", "u", sonar, _snyk(), _gg(), _bandit())
        assert any("coverage" in r.lower() for r in report["recommendations"])


class TestShowSummary:
    def test_no_issues_prints_passed(self, capsys) -> None:
        report = build_report("r", "url", _sonar(), _snyk(), _gg(), _bandit())
        show_summary(report)
        out = capsys.readouterr().out
        assert "passed" in out.lower() or "no issues" in out.lower()

    def test_issues_prints_total_count(self, capsys) -> None:
        report = build_report("r", "url", _sonar(total=3), _snyk(), _gg(), _bandit())
        show_summary(report)
        out = capsys.readouterr().out
        assert "3" in out

    def test_mixed_issues_shows_per_scanner_breakdown(self, capsys) -> None:
        report = build_report(
            "r", "url", _sonar(total=2), _snyk(vulns=1), _gg(secrets=1), _bandit(issues=3)
        )
        show_summary(report)
        out = capsys.readouterr().out
        assert "sonar=2" in out
        assert "snyk=1" in out
        assert "secrets=1" in out
        assert "bandit=3" in out

    def test_zero_scanner_counts_not_shown(self, capsys) -> None:
        report = build_report("r", "url", _sonar(total=5), _snyk(), _gg(), _bandit())
        show_summary(report)
        out = capsys.readouterr().out
        assert "sonar=5" in out
        assert "snyk=" not in out


class TestConfigPath:
    @pytest.mark.parametrize(
        "app, fragment",
        [
            ("vscode", "Code"),
            ("cursor", ".cursor"),
            ("antigravity", "antigravity"),
            ("claude", "Claude"),
            ("chatgpt", "ChatGPT"),
        ],
    )
    def test_windows_paths_contain_expected_fragment(
        self, app: str, fragment: str, monkeypatch
    ) -> None:
        monkeypatch.setenv("APPDATA", r"C:\Users\Test\AppData\Roaming")
        monkeypatch.setenv("USERPROFILE", r"C:\Users\Test")
        with patch("platform.system", return_value="Windows"):
            path = config_path(app)
        assert fragment in str(path)
        assert path.name.endswith(".json")

    @pytest.mark.parametrize(
        "app, fragment",
        [
            ("vscode", "Code"),
            ("cursor", ".cursor"),
            ("antigravity", "antigravity"),
            ("claude", "Claude"),
            ("chatgpt", "ChatGPT"),
        ],
    )
    def test_macos_paths_contain_expected_fragment(self, app: str, fragment: str) -> None:
        with patch("platform.system", return_value="Darwin"):
            path = config_path(app)
        assert fragment in str(path)
        assert path.name.endswith(".json")

    @pytest.mark.parametrize(
        "app, fragment",
        [
            ("vscode", "Code"),
            ("cursor", ".cursor"),
            ("antigravity", "antigravity"),
            ("claude", "Claude"),
            ("chatgpt", "ChatGPT"),
        ],
    )
    def test_linux_paths_contain_expected_fragment(self, app: str, fragment: str) -> None:
        with patch("platform.system", return_value="Linux"):
            path = config_path(app)
        assert fragment in str(path)
        assert path.name.endswith(".json")

    def test_unsupported_app_raises_runtime_error(self) -> None:
        with pytest.raises(RuntimeError, match="Unsupported app"):
            config_path("unknown-app")

    def test_case_insensitive_input(self, monkeypatch) -> None:
        monkeypatch.setenv("APPDATA", r"C:\Users\Test\AppData\Roaming")
        with patch("platform.system", return_value="Windows"):
            path = config_path("VSCode")
        assert "Code" in str(path)
