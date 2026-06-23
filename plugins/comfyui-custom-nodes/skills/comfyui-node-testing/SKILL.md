---
name: comfyui-node-testing
description: Use when writing, running, or debugging tests for ComfyUI custom nodes — pytest isolation, conftest mocking, or test runner issues.
---

# Testing ComfyUI Custom Nodes

ComfyUI nodes import server-side modules (`folder_paths`, `server`, `comfy_api`) at module load. Those imports fail outside a running ComfyUI process. The entire testing strategy revolves around **isolation** — intercepting those imports before pytest collects files — and a **wrapper** script that sets the correct execution context.

## Test Directory Structure

```
tests/
├── env_config.py     # Shared environment loading and path resolution
├── conftest.py       # Module-level mocking — loads before collection
├── pytest.ini        # Overrides parent-scope pytest config
├── run_tests.py      # Wrapper: venv, cwd isolation, server lifecycle
├── fixtures/         # Workflow JSON fixtures and sample data
│   └── workflows/    # API-format workflow fixtures for E2E tests
├── unit/             # Fast, isolated tests (< 1s each)
└── integration/      # Heavy tests (node registration, server, FFmpeg, etc.)
```

Template files for config files: [references/](references/).

## Prerequisites

Tests must run in an environment containing ComfyUI packages and test dependencies. Install them in the main ComfyUI virtual environment:

```bash
# Activate the ComfyUI virtual environment and install testing dependencies
pip install pytest pytest-cov
```

(Note: If a project-local `.venv` exists at the custom node root but lacks `pytest`, the test runner automatically bypasses it in favor of the ComfyUI venv.)

## Path Configuration & Local Overrides

By default, the testing environment attempts to locate ComfyUI and its virtual environment automatically using standard layout fallbacks relative to the custom node folder. For custom layouts or standalone environments, developers can define local overrides without modifying tracked files:

1. Create a `tests/.env` or `tests/.env.local` file.
2. Add your environment path variables:

```env
# Root directory of ComfyUI
COMFYUI_TEST_COMFY_ROOT=/path/to/ComfyUI

# Path to the virtual environment python executable
COMFYUI_TEST_VENV_PYTHON=/path/to/ComfyUI/venv/bin/python

# Force CPU mode even when CUDA is available (useful for CI)
COMFYUI_TEST_FORCE_CPU=1
```

These files are ignored by git, allowing developers to maintain custom configurations across different development machines.

## Execution: The Wrapper

> **Never call `pytest` directly from the package root.** The wrapper activates the ComfyUI venv via `env_config.py`, isolates `cwd` to `tests/`, and auto-starts a server for integration runs.

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

The wrapper auto-detects the platform and resolves the venv binary (`venv/Scripts/python` on Windows, `venv/bin/python` on Linux/macOS). See [run_tests.py](references/run_tests.py) for the runner template and [env_config.py](references/env_config.py) for path resolution.

> [!IMPORTANT]
> **Robust Virtualenv Verification**: A project-local `.venv` (created for editor/linting support) might exist at the custom node root but lack testing dependencies. A naive check for `.venv` existence will select it and crash. To prevent this, the wrapper's auto-detection logic executes a fast subprocess check to verify `pytest` is importable inside candidate virtual environments before routing execution. If a local environment lacks `pytest`, it is bypassed in favor of ComfyUI's main virtual environment.

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

## Workflow Formats & E2E Execution

ComfyUI uses two JSON formats for workflows:

- **GUI format** — exported by the browser UI via "Save". Contains `nodes` (array of dicts with `id`, `type`, `pos`, `widgets_values`) and `links` (array of connection tuples). **Not executable via the `/prompt` API.**
- **API format** — exported via "Save (API Format)" or Dev Mode enabled + "Save (API Format)". A flat dictionary `{nodeId: {class_type, inputs}}` where inputs reference other nodes as `[source_node_id, output_index]` tuples. **This is what `/prompt` accepts.**

### Auto-conversion

The reference `ComfyUIApiClient` in [conftest.py](references/conftest.py) detects GUI-format workflows and converts them automatically using the server's `/object_info` endpoint to resolve widget input ordering. This means test code and agents can load either format:

```python
@pytest.mark.integration
def test_workflow_e2e(api_client, workflow_fixtures_path):
    """Execute a workflow and verify completion — works with GUI or API format."""
    workflow_path = workflow_fixtures_path / "my_workflow.json"
    with open(workflow_path) as f:
        workflow = json.load(f)
    result = api_client.execute_workflow(workflow, timeout=300)
    assert result is not None
```

### Output node requirement

ComfyUI refuses to execute workflows that lack at least one node with `OUTPUT_NODE = True`. The API client auto-injects a `PreviewAny` node on the deepest leaf if no output node exists. If `PreviewAny` is not installed on the server, injection is skipped and the server will return a `prompt_no_outputs` error naturally.

### Workflow fixtures

Store workflow fixtures in `tests/fixtures/workflows/`. Prefer API format for checked-in fixtures (smaller, deterministic). When the user provides a GUI-format export, the auto-conversion handles it transparently.

## GPU & Device Routing

When the test runner spawns its own ComfyUI server (no server already running), it probes CUDA availability via the venv python and launches accordingly:

- **CUDA available**: Server starts on GPU (default — no `--cpu` flag).
- **No CUDA**: Server starts with `--cpu` automatically.
- **Force CPU**: Set `COMFYUI_TEST_FORCE_CPU=1` in `.env.local` for CI or headless machines.

> [!IMPORTANT]
> **Prefer a running server.** If ComfyUI is already running (e.g., the developer's GPU instance on port 8188), the test harness reuses it — no subprocess is spawned and no device probe runs. Before running E2E integration tests with large models, verify a GPU server is running: `curl http://127.0.0.1:8188/system_stats`. Never hardcode `--cpu` in the server launch arguments.

## Test Coverage Configuration

Bundled third-party libraries (e.g., model code or subpackages) can heavily pollute coverage results. Configure exclusions using globstar (`**/`) rules to recursively match directories:

1. **Local config**: Because `run_tests.py` isolates context by changing directory to `tests/`, place a `.coveragerc` file inside `tests/` so `pytest-cov` automatically picks it up during execution.
2. **Globstar syntax**: Slashes are required to match directory paths instead of filenames. Use double asterisks (`**/`) to match multi-level folders regardless of relative or absolute path variations.

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
| `ModuleNotFoundError: folder_paths` | Node imports ComfyUI internals at load | Add the module to `conftest.py` mock list |
| `No tests found` | Parent `pytest.ini` overrides test discovery | Ensure `tests/pytest.ini` exists with `testpaths = .` |
| `ImportError: attempted relative import` | `pytest` run directly from package root | Use `run_tests.py` wrapper — it sets the correct `sys.path` |
| `TypeError` on `class MyNode(io.ComfyNode)` | `io.ComfyNode` mocked as MagicMock, not a real type | Use `type("ComfyNode", (object,), {})` in conftest structural mock |
| `AttributeError` on mocked module | Test calls a method the MagicMock doesn't spec | Add the attribute to the mock or use a targeted fixture |
| `Integration tests hang / timeout` | Subprocess stdout buffer filled up (`subprocess.PIPE` without consumption) | Redirect subprocess output to a file (e.g. `tests/comfyui_server.log`) or `DEVNULL` |
| `Nodes not registered in server subprocess` | Subprocess inherits testing-bypass environment flags (`COMFYUI_TESTING=1`) | Strip test-specific environment flags from the environment dict passed to the subprocess |
| `Manual scripts pollute pytest run / crash` | Helper/debug scripts match `test_*.py` and are scanned by pytest | Relocate helper scripts to `tests/diagnostics/`, rename them to not match the `test_` prefix, or restrict `python_files` in `tests/pytest.ini` to specific subdirectories (e.g., `unit/test_*.py` and `integration/test_*.py`) |
| `400 prompt_no_outputs` on workflow execution | Workflow has no node with `OUTPUT_NODE = True` | Use `execute_workflow()` (auto-injects `PreviewAny`), or manually add an output node to the workflow fixture |
| `Workflow queue returns 400 / validation error` | Workflow is in GUI format (has `nodes`/`links` arrays) | Use `execute_workflow()` (auto-converts), or re-export from ComfyUI with Dev Mode → "Save (API Format)" |
| `E2E tests extremely slow / timeout` | Server launched with `--cpu` for large models | Remove `--cpu`; ensure CUDA is available or pre-start a GPU server on port 8188 |
| `Coverage report includes 3rd-party code / massive statement counts` | `pytest-cov` performs source discovery and includes all subfolders in the target | Add a `tests/.coveragerc` or `pyproject.toml` containing globstar omit patterns |
| `Omit patterns in coveragerc are ignored` | Patterns lack slashes (matching basename only) or use `*` which does not cross folders | Use double asterisks `**/folder_name/**` (globstar) for multi-level recursive matching |

## See Also

- `comfyui-node-packaging` – Project structure and entry points
- `comfyui-node-lifecycle` – Execution flow (useful for integration test design)
- `comfyui-node-basics` – Node class structure
