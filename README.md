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

<div align="center">

[![CI](https://github.com/areebahmeddd/superbox.ai/actions/workflows/ci.yaml/badge.svg?branch=prod)](https://github.com/areebahmeddd/superbox.ai/actions/workflows/ci.yaml)
[![PyPI version](https://img.shields.io/pypi/v/superbox)](https://pypi.org/project/superbox)
[![PyPI downloads](https://img.shields.io/pypi/dm/superbox)](https://pypi.org/project/superbox)
[![Python](https://img.shields.io/pypi/pyversions/superbox)](https://pypi.org/project/superbox)
[![Go](https://img.shields.io/badge/go-1.26-00ADD8?logo=go&logoColor=white)](https://go.dev)
[![License](https://img.shields.io/github/license/areebahmeddd/superbox.ai)](LICENSE)

</div>

# 🧰 SuperBox

**SuperBox** (inspired by [Docker Hub](https://hub.docker.com)) helps you discover, deploy, and test MCPs in isolated sandboxes ( [Demo Video]() ). It includes:

- A Python (Click) CLI to initialize metadata, run security scans, push to a registry (R2), search, and configure popular AI clients (VS Code, Cursor, Antigravity, Claude, ChatGPT)
- A Golang (Gin) backend to list/get/create MCP servers with optional pricing and security reports
- A Cloudflare Worker + Durable Object executor that runs MCP servers on demand directly from their Git repositories using a lightweight TypeScript interpreter (Cloudflare Workers blocks `eval()` and exceeds the WASM bundle size limit, making Pyodide unusable)

Why this project:

- There's no centralized MCP registry to discover all MCPs, and many lack clear usage docs.
- MCPs on our platform pass a 5-step security/quality check (SonarQube, Bandit, GitGuardian) to reduce vulnerabilities and promote best practices.
- Unlike MCPs that run locally on your machine, MCP servers here execute in sandboxed environments and return responses securely.

## Key Features

- **Central MCP Registry**: R2-backed registry with per-server JSON for easy discovery and portability.
- **Sandboxed Execution**: MCP servers run in Cloudflare Durable Objects and return responses securely. The executor supports Python (`requests`-based) and JavaScript/TypeScript (`fetch()`-based) tools; see `cloudflare/README.md` for the full scope.
- **Security Pipeline (5-step)**: SonarQube, Bandit, and GitGuardian checks with a unified report.
- **One-Command Publish**: `superbox push` scans, discovers tools, and uploads a unified record to R2.
- **Client Auto-Config**: `superbox pull --client cursor|vscode|...` writes correct MCP config pointing to the Cloudflare Worker.
- **Terminal Runner**: `superbox run --name <server>` starts an interactive prompt against the Cloudflare executor.
- **Live Logs**: `superbox logs --name <server>` shows instructions for streaming logs via `wrangler tail`.
- **Tool Discovery**: Regex-based discovery across Python source (`@mcp.tool` decorators) and TypeScript/JavaScript source (`server.tool` / Zod schemas), plus `package.json` metadata.

## 📚 Documentation

**For complete documentation, setup guides, API references, and CLI usage:**

🔗 **[https://superbox.1mindlabs.org/docs](https://superbox.1mindlabs.org/docs)**

## 📄 Research Paper

The IEEE research paper for SuperBox is available in the [`ieee/`](ieee/) directory:

- [`paper.pdf`](ieee/paper.pdf) - compiled paper
- [`paper.tex`](ieee/paper.tex) - LaTeX source

## 🗂️ Project Structure

```text
.
├── docs/                       # Documentation (INSTALL.md, SETUP.md)
├── ieee/                       # IEEE research paper (paper.pdf, paper.tex)
├── src/
│   └── superbox/
│       ├── cli/                # CLI: init, auth, push, pull, run, search, inspect, test, logs
│       │   ├── commands/       # CLI subcommands
│       │   └── scanners/       # SonarCloud, Bandit, ggshield, tool-discovery
│       ├── server/             # Golang (Gin) app + handlers
│       │   ├── handlers/       # servers, payment, auth, health
│       │   ├── models/         # Request/response types
│       │   ├── helpers/        # Python R2 helper
│       │   └── templates/      # Landing page
│       └── shared/             # Config, models, R2/S3-compat utils
├── pyproject.toml              # Project metadata & dependencies
├── Dockerfile                  # Server container
├── docker-compose.yaml         # Optional local stack
└── tests/                      # pytest suite - see tests/README.md
```

## 🌐 API Reference

The HTTP API provides endpoints for server management, authentication, and payments.

For complete API documentation, see:
[https://superbox.1mindlabs.org/docs/api](https://superbox.1mindlabs.org/docs/api)

## 🔧 CLI Overview

The SuperBox CLI provides commands for authentication, server management, and testing:

**Authentication:**

- `superbox auth register` - Register a new account
- `superbox auth login` - Log in (email/Google/GitHub)
- `superbox auth logout` - Log out
- `superbox auth status` - Check authentication status
- `superbox auth refresh` - Refresh authentication token

**Server Management:**

- `superbox init` - Initialize a new MCP server project
- `superbox push` - Publish server to registry
- `superbox pull` - Download and configure server for AI clients
- `superbox search` - Search for servers in registry
- `superbox inspect` - View server details and security report
- `superbox test` - Test server directly from repository (without registry)

**Execution & Monitoring:**

- `superbox run` - Run server in interactive mode
- `superbox logs` - View server execution logs

For detailed CLI documentation and usage examples, see:
[https://superbox.1mindlabs.org/docs/cli](https://superbox.1mindlabs.org/docs/cli)

## 📦 Installation

```bash
pip install superbox
```

- **PyPI:** [https://pypi.org/project/superbox](https://pypi.org/project/superbox)
- **npm:** [https://npmjs.com/package/superbox](https://npmjs.com/package/superbox)

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
