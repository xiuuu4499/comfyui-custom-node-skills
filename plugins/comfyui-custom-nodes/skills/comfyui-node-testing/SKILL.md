---
name: comfyui-node-testing
description: Use when writing, running, or debugging tests for ComfyUI custom nodes — pytest isolation, conftest mocking, or test runner issues.
---

# Testing ComfyUI Custom Nodes

ComfyUI nodes import server-side modules (`folder_paths`, `server`, `comfy_api`) at module load. Those imports fail outside a running ComfyUI process. The entire testing strategy revolves around **isolation** — intercepting those imports before pytest collects files — and a **wrapper** script that sets the correct execution context.

## Test Directory Structure

```
tests/
├── conftest.py       # Module-level mocking — loads before collection
├── pytest.ini        # Overrides parent-scope pytest config
├── run_tests.py      # Wrapper: venv, cwd isolation, server lifecycle
├── unit/             # Fast, isolated tests (< 1s each)
└── integration/      # Heavy tests (node registration, server, FFmpeg, etc.)
```

Template files for all three config files: [references/](references/).

## Execution: The Wrapper

> **Never call `pytest` directly from the package root.** The wrapper activates the ComfyUI venv, isolates `cwd` to `tests/`, and auto-starts a server for integration runs.

```bash
# From the custom node directory:
cd custom_nodes/<NODE_PACKAGE_NAME>

# All tests (auto-starts server if needed)
python tests/run_tests.py --all

# Unit tests only — no server, no heavy dependencies
python tests/run_tests.py unit/

# Integration tests only
python tests/run_tests.py integration/
```

The wrapper auto-detects the platform and resolves the venv binary (`venv/Scripts/python` on Windows, `venv/bin/python` on Linux/macOS). See [run_tests.py](references/run_tests.py) for the full template.

## Isolation via conftest.py

`conftest.py` sits at the `tests/` root and runs before pytest scans any test file. It intercepts ComfyUI-internal imports via `sys.modules`:

**Two kinds of mock are needed:**

1. **Simple MagicMock** — for modules used only for side effects (`folder_paths`, `server`, `comfy.model_management`).
2. **Structural mock** — when node code inherits from a module attribute. `comfy_api.latest.io.ComfyNode` must be a real `type()`, not a MagicMock, or `class MyNode(io.ComfyNode)` crashes.

```python
# Structural mock — io.ComfyNode must be inheritable
mock_api = MagicMock()
mock_api.latest.io.ComfyNode = type("ComfyNode", (object,), {})
mock_api.latest.io.NodeOutput = lambda *args: args
sys.modules["comfy_api"] = mock_api
sys.modules["comfy_api.latest"] = mock_api.latest
```

Add entries as new `ModuleNotFoundError` messages surface — the traceback names the exact module to mock. See [conftest.py](references/conftest.py) for a complete template with typed inputs, marker registration, and the integration API client.

### pytest.ini

A [pytest.ini](references/pytest.ini) inside `tests/` overrides any parent-scope config. ComfyUI's root often carries a `pytest.ini` that conflicts with custom node test discovery.

## Unit vs Integration Tests

### Unit (`@pytest.mark.unit`)

Validate calculations, utility functions, and internal logic **without touching ComfyUI**. Keep testable logic in isolated modules (`utils/`, `backend/`) separated from node definitions to avoid accidentally pulling in server imports.

```python
@pytest.mark.unit
def test_normalize_scores():
    from package.utils.math import normalize_scores
    assert normalize_scores(0.5) == 0.5
```

### Integration (`@pytest.mark.integration`)

Verify node registration, pipeline outputs, API endpoints, or external binaries. The wrapper auto-starts a server; the `api_client` fixture (session-scoped, lazy-imported) skips the suite if the server is unreachable.

```python
@pytest.mark.integration
def test_node_registered(api_client):
    assert api_client.node_exists("MyNode_UniqueID")
```

## Diagnostics

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: folder_paths` | Node imports ComfyUI internals at load | Add the module to `conftest.py` mock list |
| `No tests found` | Parent `pytest.ini` overrides test discovery | Ensure `tests/pytest.ini` exists with `testpaths = .` |
| `ImportError: attempted relative import` | `pytest` run directly from package root | Use `run_tests.py` wrapper — it sets the correct `sys.path` |
| `TypeError` on `class MyNode(io.ComfyNode)` | `io.ComfyNode` mocked as MagicMock, not a real type | Use `type("ComfyNode", (object,), {})` in conftest structural mock |
| `AttributeError` on mocked module | Test calls a method the MagicMock doesn't spec | Add the attribute to the mock or use a targeted fixture |
| `Integration tests hang / timeout` | Subprocess stdout buffer filled up (`subprocess.PIPE` without consumption) | Redirect subprocess output to a file (e.g. `tests/comfyui_server.log`) or `DEVNULL` |
| `Nodes not registered in server subprocess` | Subprocess inherits testing-bypass environment flags (`COMFYUI_TESTING=1`) | Strip test-specific environment flags from the environment dict passed to the subprocess |
| `Manual scripts pollute pytest run / crash` | Helper/debug scripts match `test_*.py` and are scanned by pytest | Relocate helper scripts to `tests/diagnostics/` or rename them to not match the `test_` prefix |

## See Also

- `comfyui-node-packaging` – Project structure and entry points
- `comfyui-node-lifecycle` – Execution flow (useful for integration test design)
- `comfyui-node-basics` – Node class structure
