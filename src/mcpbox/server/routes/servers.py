"""Server Management Routes"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from mcpbox.shared.config import Config
from mcpbox.shared.models import CreateServerRequest
from mcpbox.shared.s3 import (
    list_servers as s3_list_servers,
    get_server as s3_get_server,
    upsert_server,
)

router = APIRouter()

_cfg = Config()
S3_BUCKET = _cfg.S3_BUCKET_NAME


@router.get("/{server_name}")
async def get_server(server_name: str) -> JSONResponse:
    """Get detailed information about a specific MCP server"""
    try:
        server = s3_get_server(S3_BUCKET, server_name)

        if not server:
            raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")

        return JSONResponse(content={"status": "success", "server": server})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching server info: {str(e)}")


@router.get("")
async def list_servers() -> JSONResponse:
    """List all MCP servers from S3 bucket"""
    try:
        server_map = s3_list_servers(S3_BUCKET)

        if not server_map:
            return JSONResponse(content={"status": "success", "total": 0, "servers": []})

        server_list = []
        for server in server_map.values():
            server_info = {
                "name": server.get("name"),
                "version": server.get("version"),
                "description": server.get("description"),
                "author": server.get("author"),
                "lang": server.get("lang"),
                "license": server.get("license"),
                "entrypoint": server.get("entrypoint"),
                "repository": server.get("repository"),
            }

            if "tools" in server and server["tools"]:
                server_info["tools"] = server["tools"]

            if "pricing" in server and server["pricing"]:
                server_info["pricing"] = server["pricing"]
            else:
                server_info["pricing"] = {"currency": "", "amount": 0}

            if "security_report" in server and server["security_report"]:
                server_info["security_report"] = server["security_report"]

            server_list.append(server_info)

        return JSONResponse(
            content={"status": "success", "total": len(server_list), "servers": server_list}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching servers: {str(e)}")


@router.post("")
async def create_server(server: CreateServerRequest) -> JSONResponse:
    """Create a new MCP server and add it to S3"""
    try:
        existing = s3_get_server(S3_BUCKET, server.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Server '{server.name}' already exists")

        new_server = {
            "name": server.name,
            "version": server.version,
            "description": server.description,
            "author": server.author,
            "lang": server.lang,
            "license": server.license,
            "entrypoint": server.entrypoint,
            "repository": {"type": server.repository.type, "url": server.repository.url},
            "meta": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        new_server["pricing"] = {
            "currency": server.pricing.currency,
            "amount": server.pricing.amount,
        }

        if server.tools:
            new_server["tools"] = server.tools

        upsert_server(S3_BUCKET, server.name, new_server)

        return JSONResponse(
            content={"status": "success", "message": "Server created", "server": new_server},
            status_code=201,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating server: {str(e)}")
