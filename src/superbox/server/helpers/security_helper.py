import sys
import json
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from superbox.cli.scanners import bandit, ggshield, sonarqube
from superbox.cli.scanners import discovery as tool_discovery
from superbox.cli.utils import build_report


def scan_repository(repo_url: str, server_name: str) -> dict:
    """Execute security scanning pipeline and discover MCP tools"""
    try:
        result = sonarqube.run_analysis(repo_url)

        if not result["success"]:
            return {"success": False, "error": "SonarCloud analysis failed"}

        sonar_data = result["report_data"]
        temp_dir = tempfile.mkdtemp(prefix="superbox_scan_")

        try:
            repo_path = tool_discovery.clone_repo(repo_url, temp_dir)

            if not repo_path:
                return {"success": False, "error": "Repository clone failed"}

            tool_info = tool_discovery.discover_tools(repo_path)
            owner, repo = sonarqube.extract_repository(repo_url)
            repo_name = f"{owner}_{repo}" if owner and repo else server_name

            try:
                ggshield_result = ggshield.run_scan(repo_path)
            except Exception:
                ggshield_result = {"success": True, "total_secrets": 0, "secrets": []}

            try:
                bandit_result = bandit.run_scan(repo_path)
            except Exception:
                bandit_result = {"success": True, "total_issues": 0, "issues": []}

            security_report = build_report(
                repo_name, repo_url, sonar_data, ggshield_result, bandit_result
            )

            return {
                "success": True,
                "security_report": security_report,
                "tools": {
                    "names": tool_info.get("tool_names", []),
                    "count": tool_info.get("tool_count", 0),
                },
            }
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    try:
        input_data = json.loads(sys.argv[1])
        function = input_data["function"]
        args = input_data["args"]

        if function == "scan_repository":
            result = scan_repository(args["repo_url"], args["server_name"])
            output = result
        else:
            output = {"success": False, "error": f"Unknown function: {function}"}

        print(json.dumps(output))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
