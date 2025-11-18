# SuperBox – Installation & Quick Start

> Works on Windows, macOS, and Linux. Examples below use Windows PowerShell; adapt paths/activate scripts for your OS.

## 1) Prerequisites

- Python 3.11+ (for CLI)
- Go 1.21+ (for server)
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

## 3) Install SuperBox CLI

```powershell
python -m pip install -e .[cli]
```

Optional (dev tools):

```powershell
python -m pip install -e .[dev]
```

## 4) Configure environment (.env)

Create a `.env` in the working directory (the server loads it at startup; CLI commands expect it in the current directory). Use the following keys:

```dotenv
# SuperBox API (required for auth/device login callbacks)
SUPERBOX_API_URL=http://localhost:8000/api/v1

# AWS (required for S3-backed registry)
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=your-bucket

# Lambda base URL for the executor endpoint (API Gateway URL)
LAMBDA_BASE_URL=https://your-api.example.com/run

# Scanners (required for `superbox push`)
SONAR_TOKEN=...
SONAR_ORGANIZATION=...
GITGUARDIAN_API_KEY=...

# Payments (required)
RAZORPAY_KEY_ID=...
RAZORPAY_KEY_SECRET=...
```

Notes:

- Server calls `load_env()` on startup, then reads values via `Config()` in `superbox.shared.config`.
- CLI commands (`push`, `pull`, `search`) call `load_env()` from the current directory; run them where your `.env` exists.

## 5) Run the server

From the `src/superbox/server` directory:

```powershell
cd src\superbox\server
go run .
```

Or build and run:

```powershell
cd src\superbox\server
go build -o server.exe .
.\server.exe
```

Then open:

- Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Root: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

If `.env` is incomplete or missing, server health will be degraded and routes depending on missing configuration will fail.

## 6) Use the CLI

General help:

```powershell
superbox --help
```

Initialize a project config:

```powershell
superbox init
```

Push a server definition (scan + upload to S3):

```powershell
superbox push --name <server-name>
# The repository URL is read from superbox.json created by `superbox init`
```

Pull and configure client MCP settings:

```powershell
superbox pull --name <server-name> --client cursor
# Supported clients: vscode | cursor | windsurf | claude | chatgpt
```

Run a server interactively from the terminal:

```powershell
superbox run --name <server-name>
# Type your prompt at "> ", e.g., "What's the weather today?" and view the response
```

Search available servers:

```powershell
superbox search
```

Inspect a server (open repository URL in browser):

```powershell
superbox inspect --name <server-name>
```

## 7) Troubleshooting

- Missing env: ensure `.env` is present with the variables above.
- AWS permissions: verify bucket exists and IAM creds allow GetObject/PutObject for the bucket.
- Sonar scanner: requires `sonar-scanner` on PATH; set `SONAR_TOKEN` and `SONAR_ORGANIZATION`.
- ggshield/Bandit CLIs: install these tools if you plan to run those scans (`ggshield`, `bandit` in PATH).

## 8) Uninstall / Clean up

```powershell
deactivate   # leave venv
# remove .venv or reinstall with a fresh environment if needed
```
