import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from superbox.cli.scanners import ggshield


def _proc(stdout: str = "", returncode: int = 0, stderr: str = "") -> MagicMock:
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    m.stderr = stderr
    return m


def _secret(type_: str = "api_key", line: int = 5) -> dict:
    return {"type": type_, "validity": "valid", "start_line": line}


def _scan_output(secrets: list) -> str:
    return json.dumps([{"filename": "main.py", "secrets": secrets}])


class TestGGShieldRunScan:
    def test_clean_scan_empty_list_output(self, tmp_path) -> None:
        with patch(
            "superbox.cli.scanners.ggshield.subprocess.run", return_value=_proc(stdout="[]")
        ):
            result = ggshield.run_scan(str(tmp_path))
        assert result["success"] is True
        assert result["total_secrets"] == 0
        assert result["secrets"] == []

    def test_clean_scan_no_stdout(self, tmp_path) -> None:
        with patch("superbox.cli.scanners.ggshield.subprocess.run", return_value=_proc(stdout="")):
            result = ggshield.run_scan(str(tmp_path))
        assert result["success"] is True
        assert result["total_secrets"] == 0

    def test_secrets_detected_and_counted(self, tmp_path) -> None:
        secrets = [_secret("api_key"), _secret("private_key", line=12)]
        with patch(
            "superbox.cli.scanners.ggshield.subprocess.run",
            return_value=_proc(stdout=_scan_output(secrets)),
        ):
            result = ggshield.run_scan(str(tmp_path))
        assert result["total_secrets"] == 2
        assert result["secrets"][0]["type"] == "api_key"
        assert result["secrets"][1]["line"] == 12

    def test_dict_output_wrapped_to_list(self, tmp_path) -> None:
        single = {"filename": "config.py", "secrets": [_secret()]}
        with patch(
            "superbox.cli.scanners.ggshield.subprocess.run",
            return_value=_proc(stdout=json.dumps(single)),
        ):
            result = ggshield.run_scan(str(tmp_path))
        assert result["total_secrets"] == 1

    def test_multiple_files_in_output(self, tmp_path) -> None:
        output = json.dumps(
            [
                {"filename": "file1.py", "secrets": [_secret("key_a")]},
                {"filename": "file2.py", "secrets": [_secret("key_b"), _secret("key_c")]},
            ]
        )
        with patch(
            "superbox.cli.scanners.ggshield.subprocess.run", return_value=_proc(stdout=output)
        ):
            result = ggshield.run_scan(str(tmp_path))
        assert result["total_secrets"] == 3

    def test_nonzero_returncode_with_no_stdout_raises(self, tmp_path) -> None:
        with patch(
            "superbox.cli.scanners.ggshield.subprocess.run",
            return_value=_proc(stdout="", returncode=1, stderr="auth error"),
        ):
            with pytest.raises(RuntimeError, match="ggshield"):
                ggshield.run_scan(str(tmp_path))

    def test_invalid_json_raises(self, tmp_path) -> None:
        with patch(
            "superbox.cli.scanners.ggshield.subprocess.run",
            return_value=_proc(stdout="not-valid-json"),
        ):
            with pytest.raises(RuntimeError, match="invalid JSON"):
                ggshield.run_scan(str(tmp_path))

    def test_timeout_raises(self, tmp_path) -> None:
        with patch(
            "superbox.cli.scanners.ggshield.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="ggshield", timeout=60),
        ):
            with pytest.raises(RuntimeError, match="timed out"):
                ggshield.run_scan(str(tmp_path))

    def test_not_installed_raises(self, tmp_path) -> None:
        with patch(
            "superbox.cli.scanners.ggshield.subprocess.run",
            side_effect=FileNotFoundError("ggshield not found"),
        ):
            with pytest.raises(RuntimeError, match="not installed"):
                ggshield.run_scan(str(tmp_path))
