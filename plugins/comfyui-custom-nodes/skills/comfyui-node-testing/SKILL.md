---
name: comfyui-node-testing
description: Use when the user wants to write, run, or debug tests for ComfyUI custom nodes — isolation via conftest mocking, wrapper execution, or workflow format conversion.
---

# Testing ComfyUI Custom Nodes

ComfyUI nodes import server-side modules (`folder_paths`, `server`, `comfy_api`) at module load. Those imports fail outside a running ComfyUI process. The entire testing strategy revolves around **isolation** — intercepting those imports before pytest collects files.

## Core Principle: Isolation

**Isolation** means ComfyUI-internal imports never reach the real server. Two mechanisms:

1. **conftest.py** — mocks modules at collection time
2. **run_tests.py wrapper** — isolates venv, cwd, and server lifecycle

## Test Directory Structure

```
tests/
├── env_config.py     # Path resolution and .env loading
├── conftest.py       # Module mocking before collection
├── pytest.ini        # Test discovery config
├── run_tests.py      # Wrapper: venv, cwd, server
├── fixtures/
│   └── workflows/    # API or GUI format workflow JSON
├── unit/             # Fast tests (< 1s, no server)
└── integration/      # Heavy tests (server, registration, binaries)
```

Template files: [references/](references/).

## Setup

```bash
# In the ComfyUI virtual environment:
pip install pytest pytest-cov
```

## Local Path Overrides

For non-standard ComfyUI layouts, create `tests/.env.local` (gitignored):

```env
COMFYUI_TEST_COMFY_ROOT=/path/to/ComfyUI
COMFYUI_TEST_VENV_PYTHON=/path/to/ComfyUI/venv/bin/python
COMFYUI_TEST_FORCE_CPU=1
```

## Execution

> **Never call `pytest` directly.** Use the wrapper for venv activation, cwd isolation, and server management.

```bash
cd custom_nodes/<NODE_PACKAGE_NAME>
python tests/run_tests.py --all       # all tests
python tests/run_tests.py unit/       # unit only
python tests/run_tests.py integration/ # integration only
```

The wrapper verifies candidate virtualenvs have `pytest` before selection — a local `.venv` without test dependencies is bypassed for ComfyUI's main venv.

## Isolation via conftest.py

`conftest.py` runs before pytest collects any test file. It intercepts imports via `sys.modules`.

**Two mock types:**

1. **Simple MagicMock** — modules used for side effects only (`folder_paths`, `server`, `comfy.model_management`).
2. **Structural mock** — when node code inherits from a module attribute. `comfy_api.latest.io.ComfyNode` must be a real `type()`, not a MagicMock.

```python
# Structural mock — io.ComfyNode must be inheritable
mock_api = MagicMock()
mock_api.latest.io.ComfyNode = type("ComfyNode", (object,), {})
mock_api.latest.io.NodeOutput = lambda *args: args
sys.modules["comfy_api"] = mock_api
sys.modules["comfy_api.latest"] = mock_api.latest
```

**Completion criterion:** Every `ModuleNotFoundError` from test collection is resolved by adding the named module to `conftest.py`.

See [conftest.py](references/conftest.py) for the full template.

## Unit vs Integration Tests

### Unit (`@pytest.mark.unit`)

Validate calculations and utility functions **without ComfyUI imports**. Keep testable logic in isolated modules (`utils/`, `backend/`).

```python
@pytest.mark.unit
def test_normalize_scores():
    from package.utils.math import normalize_scores
    assert normalize_scores(0.5) == 0.5
```

### Integration (`@pytest.mark.integration`)

Verify node registration, pipeline outputs, API endpoints, or external binaries. The wrapper auto-starts a server; the `api_client` fixture skips if unreachable.

```python
@pytest.mark.integration
def test_node_registered(api_client):
    assert api_client.node_exists("MyNode_UniqueID")
```

## Workflow Formats & E2E Execution

ComfyUI uses two JSON formats:

- **GUI format** — has `nodes` (array) and `links`. Not executable via `/prompt`.
- **API format** — flat dict `{nodeId: {class_type, inputs}}`. Executable.

### Auto-conversion

`ComfyUIApiClient.execute_workflow()` detects GUI format and converts via `/object_info`. Test code can load either format transparently:

```python
@pytest.mark.integration
def test_workflow_e2e(api_client, workflow_fixtures_path):
    workflow_path = workflow_fixtures_path / "my_workflow.json"
    with open(workflow_path) as f:
        workflow = json.load(f)
    result = api_client.execute_workflow(workflow, timeout=300)
    assert result is not None
```

### Output node requirement

Workflows need at least one node with `OUTPUT_NODE = True`. The client auto-injects `PreviewAny` on the deepest leaf if missing. If `PreviewAny` is not installed, the server returns `prompt_no_outputs`.

Store fixtures in `tests/fixtures/workflows/`. Prefer API format (smaller, deterministic).

## GPU & Device Routing

The wrapper probes CUDA via the venv python and launches accordingly:

- **CUDA available** — server runs on GPU (default).
- **No CUDA** — server runs with `--cpu`.
- **Force CPU** — set `COMFYUI_TEST_FORCE_CPU=1` for CI.

> **Prefer a running server.** If ComfyUI is already running on port 8188, the harness reuses it — no subprocess spawned.

## Test Coverage

Place `.coveragerc` in `tests/` (the wrapper changes cwd there). Use globstar patterns for recursive excludes:

```ini
# tests/.coveragerc
[run]
omit =
    **/voicefixer_bundled/**
    **/tests/**
```

## Diagnostics

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: folder_paths` | Missing conftest mock | Add module to `conftest.py` |
| `TypeError` on `class MyNode(io.ComfyNode)` | `io.ComfyNode` is MagicMock, not a type | Use `type("ComfyNode", (object,), {})` |
| `ImportError: relative import` | pytest run from package root | Use `run_tests.py` wrapper |
| `Integration tests hang` | Subprocess stdout buffer full | Redirect server output to file or `DEVNULL` |
| `400 prompt_no_outputs` | No `OUTPUT_NODE = True` | Use `execute_workflow()` (auto-injects) |
| `Workflow validation error` | GUI format sent to `/prompt` | Use `execute_workflow()` (auto-converts) |
| `Coverage includes 3rd-party` | Missing omit patterns | Add `**/folder/**` to `.coveragerc` |

## See Also

- `comfyui-node-packaging` – Project structure and entry points
- `comfyui-node-lifecycle` – Execution flow
- `comfyui-node-basics` – Node class structure
