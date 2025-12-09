import os
import json
import subprocess
from typing import Any, Dict

from superbox.shared.config import Config


def run_scan(repo_path: str) -> Dict[str, Any]:
    print("[GGShield] Scanning repository")
    cfg = Config()
    env = dict(os.environ)
    env["GITGUARDIAN_API_KEY"] = cfg.GITGUARDIAN_API_KEY

    cmd = ["ggshield", "secret", "scan", "repo", repo_path, "--json", "--exit-zero"]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, env=env, cwd=repo_path
        )

        if result.returncode != 0 and not result.stdout:
            error_msg = result.stderr.strip() if result.stderr else "Scan failed"
            raise RuntimeError(f"ggshield: {error_msg}")

        if not result.stdout:
            return {"success": True, "total_secrets": 0, "secrets": []}

        try:
            scan_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise RuntimeError("ggshield returned invalid JSON")

        secrets_found = []
        total_secrets = 0

        if isinstance(scan_data, dict):
            scan_data = [scan_data]

        if isinstance(scan_data, list):
            for item in scan_data:
                if isinstance(item, dict):
                    secrets = item.get("secrets", [])
                    total_secrets += len(secrets)
                    for secret in secrets:
                        secrets_found.append(
                            {
                                "type": secret.get("type", "unknown"),
                                "validity": secret.get("validity", "unknown"),
                                "file": item.get("filename", "unknown"),
                                "line": secret.get("start_line", 0),
                            }
                        )

        return {
            "success": True,
            "total_secrets": total_secrets,
            "secrets": secrets_found,
        }
    except subprocess.TimeoutExpired:
        raise RuntimeError("ggshield scan timed out")
    except FileNotFoundError:
        raise RuntimeError("ggshield is not installed")
