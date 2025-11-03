"""Server Management Routes"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from mcpbox.shared.config import Config
from mcpbox.shared.models import CreateServerRequest
from mcpbox.shared.s3 import get_registry, upsert_server

router = APIRouter()

_cfg = Config()
S3_BUCKET = _cfg.S3_BUCKET_NAME
S3_KEY = _cfg.S3_METADATA_KEY


@router.get("/{server_name}")
async def get_server(server_name: str) -> JSONResponse:
    """Get detailed information about a specific MCP server"""
    try:
        file_data = get_registry(S3_BUCKET, S3_KEY)

        if not file_data or "servers" not in file_data:
            raise HTTPException(status_code=404, detail="MCP servers database not found")

        servers = file_data.get("servers", [])
        server = next((s for s in servers if s["name"] == server_name), None)

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
        file_data = get_registry(S3_BUCKET, S3_KEY)

        if not file_data:
            return JSONResponse(content={"status": "success", "total": 0, "servers": []})

        servers = file_data.get("servers", [])

        server_list = []
        for server in servers:
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
        file_data = get_registry(S3_BUCKET, S3_KEY)

        servers = file_data.get("servers", [])
        if any(s["name"] == server.name for s in servers):
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

        upsert_server(S3_BUCKET, new_server, S3_KEY)

        return JSONResponse(
            content={"status": "success", "message": "Server created", "server": new_server},
            status_code=201,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating server: {str(e)}")
