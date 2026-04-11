# Tests

## Commands

```bash
pytest                              # single run
pytest --tb=short -q                # quiet mode
pytest --cov=superbox --cov-report=term-missing   # with coverage report
```

## Coverage

**333 tests - 89% overall coverage**

## Files

### Unit

| File                     | Covers                                                                                        |
| ------------------------ | --------------------------------------------------------------------------------------------- |
| `unit/test_config.py`    | `get_env`, `load_env`, `Config`, `validate_server`, `validate_cli`                            |
| `unit/test_models.py`    | All Pydantic models: server, auth, payment                                                    |
| `unit/test_s3.py`        | `get_server`, `save_server`, `list_servers`, `check_server`, `upsert_server`, `delete_server` |
| `unit/test_utils.py`     | `build_report`, `show_summary`, `config_path` across all 5 clients and 3 OSes                 |
| `unit/test_discovery.py` | `extract_tools`, `scan_repo`, `scan_package`, `discover_tools`, `clone_repo`                  |
| `unit/test_bandit.py`    | `run_scan` - all severity paths, CWE extraction, timeout, not-installed                       |
| `unit/test_ggshield.py`  | `run_scan` - multi-file output, all exception paths                                           |
| `unit/test_snyk.py`      | `run_scan` - HTTP 200/401/404/500, sorting, CVE wrapping, network error                       |
| `unit/test_sonarqube.py` | All 10 functions including `create_report` and `run_analysis`                                 |
| `unit/test_cli_main.py`  | CLI group registration, `display_banner`, `main` entry point                                  |

### Integration

| File                          | Covers                                                           |
| ----------------------------- | ---------------------------------------------------------------- |
| `integration/test_auth.py`    | `login`, `status`, `logout`, `refresh` via CliRunner             |
| `integration/test_init.py`    | `init` - creates config, pricing, overwrite, next-steps output   |
| `integration/test_push.py`    | `push` - full pipeline, `_check_auth` all error paths            |
| `integration/test_pull.py`    | `pull` - vscode/cursor/other clients, not-found, overwrite       |
| `integration/test_search.py`  | `search` - listing, tool count, security summary, empty registry |
| `integration/test_inspect.py` | `inspect` - browser open, fallback URL, unknown server           |
| `integration/test_logs.py`    | `logs` - wrangler instructions, follow flag, not-found hint      |
| `integration/test_run.py`     | `run` - deprecation notice, pull suggestion                      |
| `integration/test_test.py`    | `test` - vscode/cursor/other clients, entrypoint, overwrite      |

## Not covered

| File / Area                                          | Reason                                                                                                                                             |
| ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cli/commands/auth.py` - `_device_login`, `register` | OAuth device flow and OTP registration both contain `while True` polling loops with `time.sleep`. Requires multi-step mock choreography; deferred. |
| `shared/s3.py` line 80                               | `except Exception: pass` inside `list_servers` is unreachable - `get_server` already swallows all exceptions and returns `None`.                   |
| `cli/main.py` - `if __name__ == "__main__"`          | Standard guard; structurally untestable under pytest.                                                                                              |
| `server/__init__.py`                                 | FastAPI server requires a separate `TestClient` + database setup stack outside the CLI test scope.                                                 |

## Stack

| Package                                          | Version | Purpose                                  |
| ------------------------------------------------ | ------- | ---------------------------------------- |
| [pytest](https://docs.pytest.org)                | 9.0     | Test runner and assertion library        |
| [moto](https://docs.getmoto.org)                 | 5.x     | AWS S3 mock (stand-in for Cloudflare R2) |
| [freezegun](https://github.com/spulec/freezegun) | 1.x     | Deterministic timestamp assertions       |
| [pytest-cov](https://pytest-cov.readthedocs.io)  | 6.x     | Coverage reporting                       |
