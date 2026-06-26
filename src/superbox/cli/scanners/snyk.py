import os
import sys
from typing import Any

import requests

from superbox.shared.config import Config


def run_scan(repo_path: str) -> dict[str, Any]:
    """Run Snyk dependency vulnerability scan via REST API"""
    print("[Snyk] Scanning dependencies", file=sys.stderr)

    if not os.path.exists(repo_path):
        return {
            "success": False,
            "error": "Repository path not found",
            "total_vulnerabilities": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "vulnerabilities": [],
        }

    req_file = os.path.join(repo_path, "requirements.txt")
    if not os.path.exists(req_file):
        print("[Snyk] No requirements.txt found, skipping scan", file=sys.stderr)
        return {
            "success": True,
            "total_vulnerabilities": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "vulnerabilities": [],
        }

    try:
        cfg = Config()

        with open(req_file, "r") as f:
            requirements = f.read()

        url = "https://snyk.io/api/v1/test/pip"
        headers = {
            "Authorization": f"token {cfg.SNYK_API_TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {"encoding": "plain", "files": {"target": {"contents": requirements}}}

        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code == 401:
            return {
                "success": False,
                "error": "Invalid Snyk API token",
                "total_vulnerabilities": 0,
                "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "vulnerabilities": [],
            }

        if response.status_code == 404:
            return {
                "success": False,
                "error": "Snyk API endpoint not found",
                "total_vulnerabilities": 0,
                "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "vulnerabilities": [],
            }

        if response.status_code != 200:
            error_msg = f"Snyk API error: {response.status_code}"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = f"{error_msg} - {error_data['message']}"
            except Exception:
                pass

            return {
                "success": False,
                "error": error_msg,
                "total_vulnerabilities": 0,
                "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "vulnerabilities": [],
            }

        data = response.json()

        issues = data.get("issues", {}).get("vulnerabilities", [])

        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        detailed_vulns = []

        for vuln in issues:
            severity = vuln.get("severity", "low").lower()
            if severity in severity_counts:
                severity_counts[severity] += 1

            cve_list = []
            identifiers = vuln.get("identifiers", {})
            if "CVE" in identifiers:
                cve_list = (
                    identifiers["CVE"]
                    if isinstance(identifiers["CVE"], list)
                    else [identifiers["CVE"]]
                )

            detailed_vulns.append(
                {
                    "title": vuln.get("title", "Unknown vulnerability"),
                    "package": vuln.get("packageName", "Unknown"),
                    "version": vuln.get("version", "Unknown"),
                    "severity": severity,
                    "id": vuln.get("id", ""),
                    "cve": cve_list,
                    "cvss_score": vuln.get("cvssScore", 0),
                    "is_upgradable": vuln.get("isUpgradable", False),
                    "is_patchable": vuln.get("isPatchable", False),
                }
            )

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        detailed_vulns.sort(key=lambda x: severity_order.get(x["severity"], 4))

        result_data = {
            "success": len(issues) == 0,
            "total_vulnerabilities": len(issues),
            "severity_counts": severity_counts,
            "vulnerabilities": detailed_vulns,
        }

        print("[Snyk] Scan complete", file=sys.stderr)
        return result_data

    except requests.RequestException as e:
        print(f"[Snyk] API request failed: {str(e)}", file=sys.stderr)
        return {
            "success": False,
            "error": f"API request failed: {str(e)}",
            "total_vulnerabilities": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "vulnerabilities": [],
        }
    except Exception as e:
        print(f"[Snyk] Error: {str(e)}", file=sys.stderr)
        return {
            "success": False,
            "error": str(e),
            "total_vulnerabilities": 0,
            "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "vulnerabilities": [],
        }
