# SuperBox – Installation Guide

**Documentation:** [https://superbox.1mindlabs.org/docs](https://superbox.1mindlabs.org/docs)

> Works on Windows, macOS, and Linux. Commands below use Windows PowerShell; adapt paths and activation scripts for your OS.

## 1) Prerequisites

- Python 3.11+ (for CLI)
- Go 1.26+ (for server)
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

**From PyPI (end users):**

```powershell
pip install superbox
```

**From source (contributors):**

```powershell
python -m pip install -e .
```

With dev tools (pytest, ruff, pre-commit):

```powershell
python -m pip install -e .[dev]
```

## 4) Configure environment (.env)

Create a `.env` in the working directory (the server loads it at startup; CLI commands expect it in the current directory). Use the following keys:

```dotenv
# SuperBox API (required for CLI auth callbacks)
SUPERBOX_API_URL=http://localhost:8000/api/v1

# Cloudflare R2 (required for registry read/write)
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_R2_ACCESS_KEY_ID=...
CLOUDFLARE_R2_SECRET_ACCESS_KEY=...
CLOUDFLARE_R2_BUCKET_NAME=superbox-mcp-registry
CLOUDFLARE_WORKER_URL=https://superbox-executor.<your-subdomain>.workers.dev

# Firebase (required for auth)
FIREBASE_API_KEY=...
FIREBASE_PROJECT_ID=...

# OAuth (optional: enables Google/GitHub device login)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

# Scanners (required for `superbox push`)
SONAR_TOKEN=...
SONAR_ORGANIZATION=...
SNYK_API_TOKEN=...
GITGUARDIAN_API_KEY=...

# Payments (required for server)
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

## 6) Run the server via Docker

Pull the pre-built image:

```bash
docker pull areebahmeddd/superbox-be:latest
```

Run with your `.env` file:

```bash
docker run -p 8000:8000 --env-file .env areebahmeddd/superbox-be:latest
```

Or pass environment variables inline:

```bash
docker run -p 8000:8000 \
  -e AWS_REGION=ap-south-1 \
  -e AWS_ACCESS_KEY_ID=... \
  -e AWS_SECRET_ACCESS_KEY=... \
  -e S3_BUCKET_NAME=... \
  -e WEBSOCKET_URL=... \
  areebahmeddd/superbox-be:latest
```

Available tags:

- `latest`: Python 3.11-slim runner (includes CLI helper scripts)

### Via Docker Compose (recommended for local development)

From the repo root:

```bash
# Build and start
docker compose up -d

# Tail logs
docker compose logs -f

# Hot reload (syncs Python helpers instantly; rebuilds on Go source changes)
docker compose watch

# Stop
docker compose down
```

The server will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000). Environment variables are loaded from `.env` automatically.

## 7) Use the CLI

CLI documentation: [https://superbox.1mindlabs.org/docs/cli](https://superbox.1mindlabs.org/docs/cli)

**Quick verification:**

```powershell
superbox --help
```

## 8) Troubleshooting

- Missing env: ensure `.env` is present with the variables above.
- Cloudflare R2: verify the bucket exists (`wrangler r2 bucket list`) and the R2 API token has Object Read & Write permissions on the bucket.
- Sonar scanner: requires `sonar-scanner` on PATH; set `SONAR_TOKEN` and `SONAR_ORGANIZATION`.
- ggshield/Bandit/Snyk: bundled with `pip install superbox`; no separate install needed.

## 9) Run the test suite

### Run Python cli tests

```powershell
pytest -q --tb=short
```

For verbose output:

```powershell
pytest -v
```

With coverage report:

```powershell
pytest -q --tb=short --cov=superbox --cov-report=term-missing
```

### Run Go server tests

```powershell
cd src\superbox\server
go test ./handlers/... -v
```

With coverage:

```powershell
cd src\superbox\server
go test ./handlers/... -cover
```

### Test layout

```
tests/                           (Python)
├── conftest.py              # shared fixtures (mocked env, moto S3, sample data)
├── unit/
│   ├── test_shared_config.py    # get_env, load_env, Config validation
│   ├── test_shared_models.py    # Pydantic model validation
│   ├── test_shared_s3.py        # S3 CRUD via moto
│   ├── test_cli_utils.py        # build_report, show_summary, config_path
│   └── test_cli_discovery.py    # extract_tools, scan_repo, scan_package, discover_tools
├── integration/
│   ├── test_cli_init.py         # superbox init
│   ├── test_cli_auth.py         # superbox auth (login/logout/status/refresh)
│   ├── test_cli_pull.py         # superbox pull
│   ├── test_cli_push.py         # superbox push (all scanners mocked, moto S3)
│   ├── test_cli_run.py          # superbox run (deprecated command)
│   └── test_cli_search.py       # superbox search
└── aws/
    ├── test_lambda_handlers.py  # Lambda connect/disconnect/message/fetch_meta/clone_repo
    └── test_proxy.py            # WebSocket ↔ stdio proxy (pytest-asyncio)

src/superbox/server/handlers/   (Go)
├── health_test.go               # /health endpoint, degraded/healthy status
├── playground_test.go           # /playground/chat endpoint
├── payment_test.go              # HMAC signature verify, createOrder success/error
└── servers_test.go              # list/get/create/delete server CRUD
```

No real AWS credentials, Firebase keys, or scanner tokens are required. All external calls are mocked via `moto`, `unittest.mock`, and `pytest` fixtures.

## 10) Uninstall / Clean up

```powershell
deactivate   # leave venv
# remove .venv or reinstall with a fresh environment if needed
```
