"""
ComfyUI custom node test configuration.

Mocks ComfyUI-internal modules before pytest collects test files,
registers custom markers, and provides shared fixtures.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup — add the node package root so `from package.x import y` works
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# ComfyUI module mocking
# ---------------------------------------------------------------------------
# Nodes import server-side modules at load time. Mock them before pytest
# scans any test file, otherwise collection fails with ModuleNotFoundError.
#
# Two kinds of mock:
#   1. Simple MagicMock — enough for modules used only for side effects
#      (folder_paths, server, comfy.model_management).
#   2. Structural mock — needed when node code inherits from or calls specific
#      attributes (comfy_api.latest.io.ComfyNode must be a real class so
#      class MyNode(io.ComfyNode) doesn't crash).

# --- Simple mocks ---
for mod in [
    "folder_paths",
    "server",
    "comfy",
    "comfy.model_management",
    "comfy_execution.graph_utils",
]:
    sys.modules.setdefault(mod, MagicMock())

# --- comfy_api structural mock ---
if "comfy_api" not in sys.modules:
    mock_api = MagicMock()
    # io.ComfyNode must be a real type so class inheritance works
    mock_api.latest.io.ComfyNode = type("ComfyNode", (object,), {})
    mock_api.latest.io.Schema = MagicMock()
    # Typed inputs — used in define_schema()
    mock_api.latest.io.Combo.Input = MagicMock()
    mock_api.latest.io.Boolean.Input = MagicMock()
    mock_api.latest.io.Float.Input = MagicMock()
    mock_api.latest.io.Int.Input = MagicMock()
    mock_api.latest.io.String.Input = MagicMock()
    mock_api.latest.io.Image.Input = MagicMock()
    mock_api.latest.io.Image.Output = MagicMock()
    mock_api.latest.io.Mask.Output = MagicMock()
    mock_api.latest.io.NodeOutput = lambda *args: args
    sys.modules["comfy_api"] = mock_api
    sys.modules["comfy_api.latest"] = mock_api.latest


# ---------------------------------------------------------------------------
# Marker registration
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line("markers", "unit: Unit tests (fast, no server required)")
    config.addinivalue_line("markers", "integration: Integration tests (requires ComfyUI server)")


# ---------------------------------------------------------------------------
# Integration fixture — session-scoped API client
# ---------------------------------------------------------------------------

class ComfyUIApiClient:
    """Lightweight client for probing a running ComfyUI instance."""

    def __init__(self, host="127.0.0.1", port=8188):
        self.base_url = f"http://{host}:{port}"
        # Lazy import: unit tests don't need requests installed
        import requests
        self._requests = requests

    def is_healthy(self):
        try:
            resp = self._requests.get(f"{self.base_url}/system_stats", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_object_info(self):
        resp = self._requests.get(f"{self.base_url}/object_info", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def node_exists(self, node_name):
        try:
            return node_name in self.get_object_info()
        except Exception:
            return False


@pytest.fixture(scope="session")
def api_client():
    """
    Session-scoped ComfyUI API client.

    Skips the entire integration suite if the server isn't reachable.
    Uses lazy import so unit tests run even without `requests`.
    """
    client = ComfyUIApiClient()
    if not client.is_healthy():
        pytest.skip("ComfyUI server is not running on port 8188")
    return client
