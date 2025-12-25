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

**SuperBox** (inspired by [Docker Hub](https://hub.docker.com)) helps you discover, deploy, and test MCPs in isolated sandboxes. It includes:

- A Python (Click) CLI to initialize metadata, run security scans, push to a registry (S3), search, and configure popular AI clients (VS Code, Cursor, Windsurf, Claude, ChatGPT)
- A Golang (Gin) backend to list/get/create MCP servers with optional pricing and security reports
- An AWS Lambda worker that executes MCP servers on demand directly from their Git repositories

Why this project:

- There's no centralized MCP registry to discover all MCPs, and many lack clear usage docs.
- MCPs on our platform pass a 5‑step security/quality check (SonarQube, Bandit, GitGuardian) to reduce vulnerabilities and promote best practices.
- Unlike MCPs that run locally on your machine, MCP servers here execute in sandboxed environments and return responses securely.

## Key Features

- **Central MCP Registry**: S3‑backed registry with per‑server JSON for easy discovery and portability.
- **Sandboxed Execution**: MCP servers run in isolated environments and return responses securely.
- **Security Pipeline (5‑step)**: SonarQube, Bandit, and GitGuardian checks with a unified report.
- **One‑Command Publish**: `superbox push` scans, discovers tools, and uploads a unified record to S3.
- **Client Auto‑Config**: `superbox pull --client cursor|vscode|...` writes correct MCP config pointing to the Lambda endpoint.
- **Terminal Runner**: `superbox run --name <server>` starts an interactive prompt against the Lambda executor.
- **CloudWatch Logs**: `superbox logs --name <server>` fetches execution logs from AWS with real-time follow support.
- **Tool Discovery**: Regex‑based discovery across Python code and optional Node `package.json` definitions.

> **Note:** The Lambda executor currently supports Python + npm MCP servers.

## 📚 Documentation

**For complete documentation, setup guides, API references, and CLI usage:**

🔗 **[https://superbox.1mindlabs.org/docs](https://acm-aa28ebf6.mintlify.app)**

## 🗂️ Project Structure

```text
.
├── docs/                       # Documentation (INSTALL.md)
├── src/
│   └── superbox/
│       ├── cli/                # CLI: init, auth, push, pull, run, search, inspect, test, logs
│       │   ├── commands/       # CLI subcommands
│       │   └── scanners/       # SonarCloud, Bandit, ggshield, tool-discovery
│       ├── server/             # Golang (Gin) app + handlers
│       │   ├── handlers/       # servers, payment, auth, health
│       │   ├── models/         # Request/response types
│       │   ├── helpers/        # Python S3 helper
│       │   └── templates/      # Landing page
│       ├── shared/             # Config, models, S3 utils
│       └── aws/                # AWS Lambda & WebSocket proxy
│           ├── lambda.py       # Lambda handler (WebSocket executor)
│           └── proxy.py        # Local stdio-WebSocket bridge
├── pyproject.toml              # Project metadata & dependencies
├── Dockerfile                  # Server container
├── docker-compose.yaml         # Optional local stack
└── tests/                      # PyTests
```

## 🌐 API Reference

The HTTP API provides endpoints for server management, authentication, and payments.

For complete API documentation, see [https://superbox.1mindlabs.org/docs/api](https://acm-aa28ebf6.mintlify.app/api)

## 🔧 CLI Overview

The SuperBox CLI provides commands for authentication, server management, and testing:

**Authentication:**

- `superbox auth register` – Register a new account
- `superbox auth login` – Log in (email/Google/GitHub)
- `superbox auth logout` – Log out
- `superbox auth status` – Check authentication status
- `superbox auth refresh` – Refresh authentication token

**Server Management:**

- `superbox init` – Initialize a new MCP server project
- `superbox push` – Publish server to registry
- `superbox pull` – Download and configure server for AI clients
- `superbox search` – Search for servers in registry
- `superbox inspect` – View server details and security report
- `superbox test` – Test server directly from repository (without registry)

**Execution & Monitoring:**

- `superbox run` – Run server in interactive mode
- `superbox logs` – View server execution logs

For detailed CLI documentation and usage examples, see [https://superbox.1mindlabs.org/docs/cli](https://acm-aa28ebf6.mintlify.app/cli)

## 📦 Installation

See [docs/INSTALL.md](docs/INSTALL.md) for complete installation instructions.

## 📄 License

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
