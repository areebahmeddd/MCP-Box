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

**SuperBox** (inspired by [Docker Hub](https://hub.docker.com)) is an open marketplace for discovering, publishing, and executing Model Context Protocol (MCP) servers in isolated sandboxes. [Demo video]()

- A Python (Click) CLI for metadata initialization, security scanning, registry publishing, and AI client configuration (VS Code, Cursor, Antigravity, Claude, ChatGPT)
- A Go (Gin) REST API for server listing, management, and payments
- A Cloudflare Worker and Durable Object executor that fetches and runs MCP servers directly from Git repositories using an embedded TypeScript interpreter (Pyodide is excluded by the 10 MB Cloudflare bundle limit and the blocked `eval()` in V8)

## Why SuperBox

- No centralized registry exists for MCP server discovery; servers are scattered across GitHub with no enforced quality or security standard.
- MCP servers are typically run directly on the developer's machine with no scanning, validation, or isolation.
- No standardized deployment workflow exists for integrating MCP servers across AI clients and cloud environments.

## Key Features

- **Central MCP Registry**: R2-backed registry with per-server JSON for easy discovery and portability.
- **Security Pipeline (5-step)**: SonarCloud, Bandit, and GitGuardian checks with a unified report.
- **Tool Discovery**: Regex-based discovery across Python source (`@mcp.tool` decorators) and TypeScript/JavaScript source (`server.tool` / Zod schemas), plus `package.json` metadata.
- **One-Command Publish**: `superbox push` scans, discovers tools, and uploads a unified record to R2.
- **Client Auto-Config**: `superbox pull --client cursor|vscode|...` writes correct MCP config pointing to the Cloudflare Worker.
- **Sandboxed Execution**: MCP servers run in Cloudflare Durable Objects and return responses securely. The executor supports Python (`requests`-based) and JavaScript/TypeScript (`fetch()`-based) tools; see `cloudflare/README.md` for the full scope.
- **Terminal Runner**: `superbox run --name <server>` starts an interactive prompt against the Cloudflare executor.
- **Live Logs**: `superbox logs --name <server>` shows instructions for streaming logs via `wrangler tail`.

## 📚 Documentation

Complete documentation including setup guides, API reference, CLI usage, and deployment instructions:

<https://superbox.1mindlabs.org/docs>

## 📄 Research Paper

SuperBox is documented in an IEEE-format research paper covering system design, the five-stage security pipeline, execution performance benchmarks, and end-to-end publish-to-execution validation.

Available in the [`ieee/`](ieee/) directory:

- [`paper.pdf`](ieee/paper.pdf) - compiled PDF
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

The HTTP API exposes endpoints for server management, authentication, and payments. Full reference: [https://superbox.1mindlabs.org/docs/api](https://superbox.1mindlabs.org/docs/api)

## 🔧 CLI Overview

The CLI provides commands for authentication, server management, and testing:

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

## 📦 Installation

```bash
pip install superbox
```

- PyPI: <https://pypi.org/project/superbox>
- npm: <https://npmjs.com/package/superbox>

See [docs/INSTALL.md](docs/INSTALL.md) for complete installation instructions.

## Related Repositories

| Repository                                                              | Description                                          |
|-------------------------------------------------------------------------|------------------------------------------------------|
| [superbox.ai](https://github.com/areebahmeddd/superbox.ai)              | Python CLI and Go REST API                           |
| [superbox-fe](https://github.com/areebahmeddd/SuperBox-FE)              | Next.js web marketplace                              |
| [superbox-executor](https://github.com/areebahmeddd/SuperBox-Executor)  | Cloudflare Worker and Durable Object MCP executor    |
| [superbox-infra](https://github.com/areebahmeddd/SuperBox-Infra)        | OpenTofu infrastructure and deployment configuration |

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 👥 Authors

- [Areeb Ahmed](https://github.com/areebahmeddd)
- [Amartya Anand](https://github.com/amarr07)
- [Arush Verma](https://github.com/arush3218)
- [Devansh Aryan](https://github.com/devansharyan123)

**Acknowledgments:**

- [Shivansh Karan](https://github.com/spacetesla)
- [Rishi Chirchi](https://github.com/rishichirchi)
- [Avantika Kesarwani](https://github.com/avii09)
