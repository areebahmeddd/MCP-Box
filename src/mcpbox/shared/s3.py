"""S3 utilities for MCP Box"""

import json
from typing import Any, Dict, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

from mcpbox.shared.config import Config


def s3_client() -> Any:
    """Create and return S3 client using shared Config values"""
    cfg = Config()
    return boto3.client(
        "s3",
        region_name=cfg.AWS_REGION,
        aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
    )


def get_registry(bucket_name: str, key: str = "mcp.json") -> Dict[str, Any]:
    """Fetch mcp.json from S3 bucket"""
    s3 = s3_client()
    try:
        response = s3.get_object(Bucket=bucket_name, Key=key)
        content = response["Body"].read().decode("utf-8")
        return json.loads(content)
    except (s3.exceptions.NoSuchKey, ClientError):
        return {"servers": []}


def save_registry(bucket_name: str, data: Dict[str, Any], key: str = "mcp.json") -> bool:
    """Upload mcp.json to S3 bucket"""
    s3 = s3_client()
    s3.put_object(
        Bucket=bucket_name, Key=key, Body=json.dumps(data, indent=2), ContentType="application/json"
    )
    return True


def check_server(
    bucket_name: str, server_name: str, key: str = "mcp.json"
) -> Tuple[bool, Dict[str, Any]]:
    """Check if a server exists in mcp.json"""
    mcp_data = get_registry(bucket_name, key)
    servers = mcp_data.get("servers", [])

    for server in servers:
        if server.get("name") == server_name:
            return True, mcp_data

    return False, mcp_data


def find_server(
    bucket_name: str, server_name: str, key: str = "mcp.json"
) -> Optional[Dict[str, Any]]:
    """Find a server by name in mcp.json"""
    mcp_data = get_registry(bucket_name, key)
    servers = mcp_data.get("servers", [])

    for server in servers:
        if server.get("name") == server_name:
            return server

    return None


def upsert_server(bucket_name: str, server_data: Dict[str, Any], key: str = "mcp.json") -> bool:
    """Add a new server or update existing server in mcp.json"""
    mcp_data = get_registry(bucket_name, key)
    servers = mcp_data.get("servers", [])

    existing_server = None
    for s in servers:
        if s.get("name") == server_data["name"]:
            existing_server = s
            break

    if existing_server and "meta" in existing_server:
        if "meta" not in server_data:
            server_data["meta"] = {}
        server_data["meta"]["created_at"] = existing_server["meta"]["created_at"]

    servers = [s for s in servers if s.get("name") != server_data["name"]]

    servers.append(server_data)
    mcp_data["servers"] = servers

    return save_registry(bucket_name, mcp_data, key)
