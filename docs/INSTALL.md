# MCP Box – Installation & Quick Start

> Works on Windows, macOS, and Linux. Examples below use Windows PowerShell; adapt paths/activate scripts for your OS.

## 1) Prerequisites

- Python 3.11+
- Git

## 2) Create and activate a virtual environment

```powershell
# from repo root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3) Install MCP Box (server + CLI)

```powershell
python -m pip install -U pip
python -m pip install -e .[server,cli]
```

Optional (dev tools):

```powershell
python -m pip install -e .[dev]
```

## 4) Configure environment (.env)

Create a `.env` in the working directory (the server loads it at startup; CLI commands expect it in the current directory). Only add what you need to use.

```dotenv
# AWS (required for S3-backed registry)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=your-bucket
S3_METADATA_KEY=mcp.json

# Lambda base URL for the proxy endpoint
LAMBDA_BASE_URL=https://your-lambda-url.amazonaws.com

# Scanners (only if you use them)
SONAR_TOKEN=...
SONAR_ORGANIZATION=...
GITGUARDIAN_API_KEY=...

# Payments (only if you use payment routes)
RAZORPAY_KEY_ID=...
RAZORPAY_KEY_SECRET=...
```

Notes:

- Server calls `load_env()` on startup, then reads values via `Config()` in `mcpbox.shared.config`.
- CLI commands (`push`, `pull`, `search`) call `load_env()` from the current directory; run them where your `.env` exists.

## 5) Run the server

```powershell
mcpbox-server
```

Then open:

- Health: http://127.0.0.1:8000/health
- Root: http://127.0.0.1:8000/

If you run with no `.env`, the server may start but health can be degraded until you add required values.

## 6) Use the CLI

General help:

```powershell
mcpbox --help
```

Initialize a project config:

```powershell
mcpbox init
```

Push a server definition (scan + upload to S3):

```powershell
mcpbox push --name <server-name> --repo-url <https-url-or-ssh>
```

Pull and configure server in VS Code MCP config:

```powershell
mcpbox pull --name <server-name>
```

Search available servers:

```powershell
mcpbox search
```

## 7) Troubleshooting

- Missing env: ensure `.env` is present with the variables above.
- AWS permissions: verify bucket exists and IAM creds allow GetObject/PutObject on `S3_METADATA_KEY`.
- Sonar scanner: requires `sonar-scanner` on PATH; set `SONAR_TOKEN` and `SONAR_ORGANIZATION`.
- ggshield/Bandit: install those tools if you plan to run those scans.

## 8) Uninstall / Clean up

```powershell
deactivate   # leave venv
# remove .venv or reinstall with a fresh environment if needed
```
