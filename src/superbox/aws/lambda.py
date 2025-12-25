import os
import sys
import json
import shutil
import zipfile
import tempfile
import subprocess
import urllib.parse
import urllib.request

import boto3

from typing import Any, Dict

AWS_REGION = "ap-south-1"
S3_BUCKET = "superbox-mcp-registry"

_mcp_process = None
_repo_dir = None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle WebSocket events: $connect, $disconnect, $default."""
    route_key = event.get("requestContext", {}).get("routeKey")

    if route_key == "$connect":
        return handle_connect(event)
    elif route_key == "$disconnect":
        return handle_disconnect(event)
    elif route_key == "$default":
        return handle_message(event)
    else:
        return {"statusCode": 400, "body": "Unknown route"}


def handle_connect(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle WebSocket connection event."""
    global _mcp_process, _repo_dir

    try:
        query_params = event.get("queryStringParameters") or {}
        mcp_name = query_params.get("name", "")

        if not mcp_name:
            return {"statusCode": 400, "body": "Missing 'name' parameter"}

        print(f"Connect: {mcp_name}")

        return {"statusCode": 200}

    except Exception as e:
        print(f"Connect error: {e}")
        return {"statusCode": 500, "body": str(e)}


def handle_disconnect(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle WebSocket disconnection and cleanup resources."""
    global _mcp_process, _repo_dir

    print("Disconnect")

    if _mcp_process:
        _mcp_process.kill()
        _mcp_process = None

    if _repo_dir and os.path.exists(_repo_dir):
        shutil.rmtree(os.path.dirname(_repo_dir), ignore_errors=True)
        _repo_dir = None

    return {"statusCode": 200}


def handle_message(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming WebSocket messages and forward to MCP server."""
    global _mcp_process, _repo_dir

    try:
        body = event.get("body", "")
        print(f"Message: {body[:100]}")

        if not _mcp_process or _mcp_process.poll() is not None:
            print("Setting up MCP server...")

            query_params = (
                event["requestContext"].get("authorizer", {}).get("queryStringParameters", {})
            )
            if not query_params:
                query_params = event.get("queryStringParameters", {})

            mcp_name = query_params.get("name", "test-mcp")
            is_test_mode = query_params.get("test_mode", "").lower() == "true"
            repo_url = query_params.get("repo_url")

            if is_test_mode and repo_url:
                repo_url = urllib.parse.unquote(repo_url)
                metadata = {
                    "repository": {"url": repo_url},
                    "entrypoint": query_params.get("entrypoint", "main.py"),
                    "lang": query_params.get("lang", "python"),
                }
            else:
                metadata = fetch_meta(mcp_name)

            _repo_dir = clone_repo(metadata["repository"]["url"], mcp_name)
            install_deps(_repo_dir)

            _mcp_process = start_server(_repo_dir, metadata["entrypoint"], metadata["lang"])
            print("MCP server ready")

        _mcp_process.stdin.write((body + "\n").encode("utf-8"))
        _mcp_process.stdin.flush()

        response_line = _mcp_process.stdout.readline()
        response = response_line.decode("utf-8").strip()

        print(f"Response: {response[:100]}")

        connection_id = event["requestContext"]["connectionId"]
        domain = event["requestContext"]["domainName"]
        stage = event["requestContext"]["stage"]

        endpoint_url = f"https://{domain}/{stage}"
        print(f"Sending to: {endpoint_url}, connectionId: {connection_id}")

        api_gateway = boto3.client("apigatewaymanagementapi", endpoint_url=endpoint_url)

        try:
            api_gateway.post_to_connection(
                ConnectionId=connection_id, Data=response.encode("utf-8")
            )
            print("Response sent successfully")
        except Exception as post_error:
            print(f"Error posting to connection: {post_error}")
            raise

        return {"statusCode": 200}

    except Exception as e:
        print(f"Message error: {e}")
        import traceback

        traceback.print_exc()

        try:
            connection_id = event["requestContext"]["connectionId"]
            domain = event["requestContext"]["domainName"]
            stage = event["requestContext"]["stage"]

            api_gateway = boto3.client(
                "apigatewaymanagementapi", endpoint_url=f"https://{domain}/{stage}"
            )

            error_msg = json.dumps({"error": str(e), "type": type(e).__name__})
            api_gateway.post_to_connection(
                ConnectionId=connection_id, Data=error_msg.encode("utf-8")
            )
        except Exception:
            pass

        return {"statusCode": 500, "body": str(e)}


def start_server(repo_dir: str, entrypoint: str, lang: str) -> subprocess.Popen:
    """Start MCP server as a subprocess."""
    if lang.lower() != "python":
        raise ValueError(f"Unsupported language: {lang}")

    entrypoint_path = os.path.join(repo_dir, entrypoint)
    if not os.path.exists(entrypoint_path):
        raise FileNotFoundError(f"Entrypoint not found: {entrypoint}")

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{repo_dir}:{env.get('PYTHONPATH', '')}"

    pip_target = "/tmp/pip_modules"
    if os.path.exists(pip_target):
        env["PYTHONPATH"] = f"{pip_target}:{env['PYTHONPATH']}"

    process = subprocess.Popen(
        [sys.executable, entrypoint_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=repo_dir,
        env=env,
        bufsize=1,
        universal_newlines=False,
    )

    return process


def fetch_meta(mcp_name: str) -> Dict[str, Any]:
    """Fetch MCP server metadata from S3."""
    s3 = boto3.client("s3", region_name=AWS_REGION)
    key = f"{mcp_name}.json"

    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))
    except s3.exceptions.NoSuchKey:
        raise FileNotFoundError(f"MCP not found: {key}")
    except Exception as e:
        raise Exception(f"S3 error: {str(e)}")


def clone_repo(repo_url: str, mcp_name: str) -> str:
    """Download GitHub repository as ZIP and extract."""
    temp_dir = tempfile.mkdtemp(prefix=f"mcp_{mcp_name}_")
    repo_dir = os.path.join(temp_dir, "repo")

    try:
        if "github.com" not in repo_url:
            raise ValueError("Only GitHub repos supported")

        repo_url = repo_url.rstrip("/").replace(".git", "")
        zip_url = f"{repo_url}/archive/refs/heads/main.zip"
        zip_path = os.path.join(temp_dir, "repo.zip")

        urllib.request.urlretrieve(zip_url, zip_path)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(temp_dir)

        folders = [f for f in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, f))]
        if not folders:
            raise Exception("No folder in ZIP")

        os.rename(os.path.join(temp_dir, folders[0]), repo_dir)
        os.remove(zip_path)

        return repo_dir
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception(f"Clone failed: {str(e)}")


def install_deps(repo_dir: str) -> None:
    """Install Python dependencies from requirements.txt."""
    req_file = os.path.join(repo_dir, "requirements.txt")
    if not os.path.exists(req_file):
        return

    pip_target = "/tmp/pip_modules"
    os.makedirs(pip_target, exist_ok=True)

    if pip_target not in sys.path:
        sys.path.insert(0, pip_target)

    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                req_file,
                "--target",
                pip_target,
                "--upgrade",
            ],
            capture_output=True,
            timeout=180,
        )
    except Exception as e:
        print(f"Pip warning: {e}")
