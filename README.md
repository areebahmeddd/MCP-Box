<div align="center">

```text
                          _                      _
                         | |                    (_)
___ _   _ _ __   ___ _ __| |__   _____  __  __ _ _
/ __| | | | '_ \ / _ \ '__| '_ \ / _ \ \/ / / _` | |
\__ \ |_| | |_) |  __/ |  | |_) | (_) >  < | (_| | |
|___/\__,_| .__/ \___|_|  |_.__/ \___/_/\_(_)__,_|_|
         | |
         |_|
```

</div>

# 🧰 SuperBox

**Superbox** (inspired by [Docker Hub](https://hub.docker.com)) helps you discover, deploy, and test MCPs in isolated sandboxes. It includes:

- A Python (Click) CLI to initialize metadata, run security scans, push to a registry (S3), search, and configure popular AI clients (VS Code, Cursor, Windsurf, Claude, ChatGPT)
- A Golang (Gin) backend to list/get/create MCP servers with optional pricing and security reports
- An AWS Lambda worker that executes MCP servers on demand directly from their Git repositories

Why this project:

- There’s no centralized MCP registry to discover all MCPs, and many lack clear usage docs.
- MCPs on our platform pass a 5‑step security/quality check (SonarQube, Bandit, GitGuardian) to reduce vulnerabilities and promote best practices.
- Unlike MCPs that run locally on your machine, MCP servers here execute in sandboxed environments and return responses securely.

For setup and deployment, see [docs/INSTALL.md](docs/INSTALL.md).

## Key Features

- **Central MCP Registry**: S3‑backed registry with per‑server JSON for easy discovery and portability.
- **Sandboxed Execution**: MCP servers run in isolated environments and return responses securely.
- **Security Pipeline (5‑step)**: SonarQube, Bandit, and GitGuardian checks with a unified report.
- **One‑Command Publish**: `superbox push` scans, discovers tools, and uploads a unified record to S3.
- **Client Auto‑Config**: `superbox pull --client cursor|vscode|...` writes correct MCP config pointing to the Lambda endpoint.
- **Terminal Runner**: `superbox run --name <server>` starts an interactive prompt against the Lambda executor.
- **CloudWatch Logs**: `superbox logs --name <server>` fetches execution logs from AWS with real-time follow support.
- **Tool Discovery**: Regex‑based discovery across Python code and optional Node `package.json` definitions.

> NOTE: The Lambda executor currently supports Python + Npm MCP servers.

## 🗂️ Project Structure

```text
.
├── docs/                       # Documentation (see INSTALL.md)
├── src/
│   └── superbox/
│       ├── cli/                # CLI: init, auth, push, pull, run, search, inspect, test
│       │   ├── commands/       # CLI subcommands
│       │   └── scanners/       # SonarCloud, Bandit, ggshield, tool-discovery
│       ├── server/             # Golang (Gin) app + handlers
│       │   ├── handlers/       # servers, payment, auth, health
│       │   ├── models/         # Request/response types
│       │   ├── helpers/        # Python S3 helper
│       │   └── templates/      # Landing page
│       └── shared/             # Config, models, S3 utils
├── lambda.py                   # AWS Lambda handler (executor)
├── pyproject.toml              # Project metadata & extras
├── Dockerfile                  # Server container
├── docker-compose.yaml         # Optional local stack
└── tests/                      # PyTests
```

##

## 🌐 HTTP API (Server)

Base path: `/api/v1`

- **Servers**

  - `GET /servers/{name}` – get a server by name
  - `GET /servers` – list all servers
  - `POST /servers` – create a server (see schemas in `superbox.shared.models`)
  - `PUT /servers/{name}` – update an existing server (partial updates supported)
  - `DELETE /servers/{name}` – remove a server from the registry

- **Authentication**

  - `POST /auth/register` – register a new user account
  - `POST /auth/login` – login with email/password
  - `POST /auth/login/provider` – login with OAuth provider (Google/GitHub)
  - `POST /auth/refresh` – refresh authentication token
  - `GET /auth/me` – get current user profile
  - `PATCH /auth/me` – update user profile
  - `DELETE /auth/me` – delete user account
  - `POST /auth/device/start` – start OAuth device code flow
  - `POST /auth/device/poll` – poll for device authorization status
  - `GET /auth/device` – device code verification page
  - `POST /auth/device` – submit device code for verification
  - `GET /auth/device/callback/google` – Google OAuth callback
  - `GET /auth/device/callback/github` – GitHub OAuth callback

- **Payment**

  - `POST /payment/create-order` – create a Razorpay order for server purchase
  - `POST /payment/verify-payment` – verify Razorpay payment signature
  - `GET /payment/payment-status/{payment_id}` – get payment status from Razorpay

- **Other**
  - `GET /health` – config + S3 readiness
  - `GET /docs` – OpenAPI docs

## 💻 CLI Commands

The SuperBox CLI provides commands to initialize, publish, discover, and configure MCP servers.

### `superbox init`

Initialize a new `superbox.json` configuration file for your MCP server.

**Usage:**

```bash
superbox init
```

**What it does:**

- Creates `superbox.json` in the current directory
- Prompts for server metadata (name, version, description, author, language, license, entrypoint)
- Optionally adds pricing information
- Extracts repository information from GitHub URLs

**Example:**

```bash
$ superbox init
Initialize SuperBox Configuration
==================================================
Repository URL (GitHub): https://github.com/user/my-mcp
Server name: my-mcp
Version: 1.0.0
Description: My awesome MCP server
...
```

### `superbox auth`

Authenticate with the SuperBox registry using Firebase authentication. Supports email/password, Google OAuth, and GitHub OAuth.

#### `superbox auth register`

Create a new SuperBox account.

**Usage:**

```bash
superbox auth register
```

**What it does:**

- Prompts for email and password
- Creates a new Firebase account
- Automatically logs you in after registration
- Stores authentication tokens in `~/.superbox/auth.json`

**Example:**

```bash
$ superbox auth register
Email: user@example.com
Password: ********
✓ Successfully registered and logged in
```

#### `superbox auth login`

Log in to your SuperBox account.

**Usage:**

```bash
superbox auth login [--provider PROVIDER] [--email EMAIL] [--password PASSWORD]
```

**Options:**

- `--provider PROVIDER` – Authentication provider: `email`, `google`, or `github` (default: `email`)
- `--email EMAIL` – Email address (for email provider only)
- `--password PASSWORD` – Password (for email provider only)

**What it does:**

- **Email/Password**: Prompts for credentials and authenticates via Firebase
- **Google/GitHub**: Opens browser for OAuth device code flow
  - Displays a device code
  - Opens verification page in browser
  - Waits for you to complete OAuth authorization
  - Automatically detects completion and stores tokens

**Example (Email):**

```bash
$ superbox auth login --provider email
Email: user@example.com
Password: ********
✓ Successfully logged in
```

**Example (Google OAuth):**

```bash
$ superbox auth login --provider google
Opening browser for Google authentication...
Visit this URL: http://localhost:8000/api/v1/auth/device?code=XXXX-XXXX
Or enter code: XXXX-XXXX
Waiting for authentication...
✓ Successfully authenticated with Google
```

**Example (GitHub OAuth):**

```bash
$ superbox auth login --provider github
Opening browser for GitHub authentication...
Visit this URL: http://localhost:8000/api/v1/auth/device?code=XXXX-XXXX
Or enter code: XXXX-XXXX
Waiting for authentication...
✓ Successfully authenticated with GitHub
```

#### `superbox auth status`

Check your current authentication status.

**Usage:**

```bash
superbox auth status
```

**What it does:**

- Displays your logged-in email
- Shows authentication provider (email/google/github)
- Verifies token validity

**Example:**

```bash
$ superbox auth status
Logged in as: user@example.com
Provider: google
```

#### `superbox auth refresh`

Manually refresh your authentication token.

**Usage:**

```bash
superbox auth refresh
```

**What it does:**

- Uses stored refresh token to get a new ID token
- Updates authentication file with new tokens

**Example:**

```bash
$ superbox auth refresh
✓ Token refreshed successfully
```

#### `superbox auth logout`

Log out from your current session.

**Usage:**

```bash
superbox auth logout
```

**What it does:**

- Removes authentication tokens from `~/.superbox/auth.json`
- Clears current session

**Example:**

```bash
$ superbox auth logout
✓ Logged out successfully
```

> **Note:** Authentication is required for `superbox push` and other operations that modify the registry.

### `superbox push`

Publish an MCP server to the registry with comprehensive security scanning.

**Usage:**

```bash
superbox push [--name NAME] [--force]
```

**Options:**

- `--name NAME` – MCP server name (reads from `superbox.json` if not provided)
- `--force` – Force overwrite if server already exists

**What it does:**

1. Runs SonarQube analysis (creates project, scans code quality)
2. Discovers MCP tools via regex patterns in Python/Node.js code
3. Runs GitGuardian secret scan
4. Runs Bandit Python security scan
5. Generates unified security report
6. Uploads server metadata to S3 registry

**Example:**

```bash
$ superbox push --name my-mcp
Pushing server: my-mcp
Running SonarCloud analysis...
Running additional scanners...
Uploading to S3...
Push complete
```

### `superbox pull`

Pull an MCP server from the registry and configure it for your AI client.

**Usage:**

```bash
superbox pull --name NAME --client CLIENT
```

**Options:**

- `--name NAME` – MCP server name to pull (required)
- `--client CLIENT` – Target client: `vscode`, `cursor`, `windsurf`, `claude`, or `chatgpt` (required)

**What it does:**

- Fetches server metadata from S3
- Writes client-specific MCP configuration file
- Configures the client to use the Lambda executor endpoint

**Example:**

```bash
$ superbox pull --name my-mcp --client cursor
Fetching server 'my-mcp' from S3 bucket...
Success!
Server 'my-mcp' added to Cursor MCP config
Location: ~/.cursor/mcp.json
```

### `superbox run`

Start an interactive terminal session to test an MCP server.

**Usage:**

```bash
superbox run --name NAME
```

**Options:**

- `--name NAME` – MCP server name to run (required)

**What it does:**

- Connects to the Lambda executor
- Provides an interactive prompt to send requests to the MCP server
- Displays JSON responses

**Example:**

```bash
$ superbox run --name my-mcp
Connecting to MCP executor: https://lambda-url/my-mcp
Type 'exit' or 'quit' to end. Press Enter on empty line to continue.
> What tools are available?
{
  "tools": ["tool1", "tool2", "tool3"]
}
```

### `superbox search`

List all available MCP servers in the registry.

**Usage:**

```bash
superbox search
```

**What it does:**

- Lists all servers from S3 registry
- Shows repository URL, tool count, description, and security status

**Example:**

```bash
$ superbox search
======================================================================
Available MCP Servers (5 found)
======================================================================

[my-mcp]
   Repository: https://github.com/user/my-mcp
   Tools: 3
   Description: My awesome MCP server
   Security: All scans passed
```

### `superbox inspect`

Open the repository URL for a registered MCP server in your browser.

**Usage:**

```bash
superbox inspect --name NAME
```

**Options:**

- `--name NAME` – MCP server name to inspect (required)

**What it does:**

- Fetches server metadata from S3
- Opens the repository URL in your default browser

**Example:**

```bash
$ superbox inspect --name my-mcp
Fetching server 'my-mcp' from S3 bucket...
Opening repository: https://github.com/user/my-mcp
Done.
```

### `superbox test`

Test an MCP server directly from a repository URL without registry registration or security checks.

**Usage:**

```bash
superbox test --url URL --client CLIENT [--entrypoint FILE] [--lang LANGUAGE]
```

**Options:**

- `--url URL` – Repository URL of the MCP server (required)
- `--client CLIENT` – Target client: `vscode`, `cursor`, `windsurf`, `claude`, or `chatgpt` (required)
- `--entrypoint FILE` – Entrypoint file (default: `main.py`)
- `--lang LANGUAGE` – Language (default: `python`)

**What it does:**

- Bypasses S3 registry and security scanning
- Configures client to use Lambda executor with direct repo URL
- Useful for testing MCPs before publishing

**Example:**

```bash
$ superbox test --url https://github.com/user/my-mcp --client cursor
⚠️  TEST MODE - No Security Checks
This server is being tested directly and has NOT gone through:
  • Security scanning (SonarQube, Bandit, GitGuardian)
  • Quality checks
  • Registry validation
```

### `superbox logs`

Fetch and display execution logs for an MCP server from AWS CloudWatch.

**Usage:**

```bash
superbox logs --name NAME [--follow]
```

**Options:**

- `--name NAME` – MCP server name to fetch logs for (required)
- `--follow`, `-f` – Follow log output in real-time

**Example:**

```bash
$ superbox logs --name my-mcp
Fetching server 'my-mcp' from registry...
Server found: My awesome MCP server
Fetching recent logs...

================================================================================
Logs for MCP server (showing 23 entries)
================================================================================

[2025-12-10 14:30:15] Request received: my-mcp
[2025-12-10 14:30:16] Repository ready: /tmp/mcp_my-mcp_abc123/repo
[2025-12-10 14:30:18] MCP server stderr: Loading tools...
[2025-12-10 14:30:19] Request completed successfully

# Follow logs in real-time
$ superbox logs --name my-mcp --follow
```

## 📜 License

This project is licensed under the [MIT License](LICENSE).

## 👥 Authors

**Core Contributors:**

- [Areeb Ahmed](https://github.com/areebahmeddd)
- [Amartya Anand](https://github.com/amarr07)
- [Arush Verma](https://github.com/arush3218)
- [Devansh Aryan](https://github.com/devansharyan123)

**Acknowledgments:**

- [Shivansh Karan](https://github.com/spacetesla)
- [Rishi Chirchi](https://github.com/rishichirchi)
- [Avantika Kesarwani](https://github.com/avii09)
