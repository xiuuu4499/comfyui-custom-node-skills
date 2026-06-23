"""
ComfyUI custom node test configuration.

Mocks ComfyUI-internal modules before pytest collects test files,
registers custom markers, and provides shared fixtures.
"""

import os
import sys
import time
import json
import subprocess
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
    """Client for probing and executing workflows against a running ComfyUI instance.

    Handles two critical format gaps automatically:
    - GUI-format workflows are converted to API format via /object_info
    - Workflows missing OUTPUT_NODE nodes get a PreviewAny node injected
    """

    def __init__(self, host="127.0.0.1", port=8188):
        self.base_url = f"http://{host}:{port}"
        self.client_id = "pytest-test-client"
        # Lazy import: unit tests don't need requests installed
        import requests
        self._requests = requests
        self._object_info_cache = None

    # -- Health & introspection ------------------------------------------------

    def is_healthy(self):
        try:
            resp = self._requests.get(f"{self.base_url}/system_stats", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_object_info(self):
        """Fetch all registered node definitions from the running server."""
        resp = self._requests.get(f"{self.base_url}/object_info", timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _get_object_info_cached(self):
        """Session-cached /object_info to avoid repeated large fetches."""
        if self._object_info_cache is None:
            self._object_info_cache = self.get_object_info()
        return self._object_info_cache

    def node_exists(self, node_name):
        try:
            return node_name in self._get_object_info_cached()
        except Exception:
            return False

    # -- Workflow execution ----------------------------------------------------

    def queue_prompt(self, workflow):
        """Queue a workflow for execution. Accepts GUI or API format."""
        if self._is_gui_format(workflow):
            workflow = self._convert_gui_to_api(workflow)
        workflow = self._ensure_output_nodes(workflow)

        resp = self._requests.post(
            f"{self.base_url}/prompt",
            json={"prompt": workflow, "client_id": self.client_id},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def get_history(self, prompt_id):
        """Get execution history for a prompt."""
        resp = self._requests.get(
            f"{self.base_url}/history/{prompt_id}", timeout=10
        )
        resp.raise_for_status()
        return resp.json()

    def wait_for_completion(self, prompt_id, timeout=120):
        """Poll history until the prompt completes or errors."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                history = self.get_history(prompt_id)
                if prompt_id in history:
                    status = history[prompt_id].get("status", {})
                    if status.get("completed", False):
                        return history[prompt_id]
                    if status.get("status_str", "") == "error":
                        raise RuntimeError(
                            f"Workflow execution failed: {status}"
                        )
            except self._requests.RequestException:
                pass  # Server might be busy
            time.sleep(0.5)

        raise TimeoutError(
            f"Workflow did not complete within {timeout}s (prompt_id: {prompt_id})"
        )

    def execute_workflow(self, workflow, timeout=120):
        """Queue a workflow and wait for completion. Accepts GUI or API format."""
        result = self.queue_prompt(workflow)
        prompt_id = result["prompt_id"]
        return self.wait_for_completion(prompt_id, timeout)

    # -- Format detection & conversion -----------------------------------------

    @staticmethod
    def _is_gui_format(workflow):
        """GUI format has a top-level 'nodes' key containing a list of dicts."""
        return (
            isinstance(workflow.get("nodes"), list)
            and len(workflow.get("nodes", [])) > 0
            and isinstance(workflow["nodes"][0], dict)
        )

    def _convert_gui_to_api(self, gui_workflow):
        """Convert a GUI-format workflow to the API-format dict.

        Uses /object_info to resolve the positional widgets_values arrays
        into named inputs, and resolves link connections from the links array.
        """
        obj_info = self._get_object_info_cached()
        nodes = gui_workflow.get("nodes", [])
        links = gui_workflow.get("links", [])

        # Build link lookup: link_id -> (source_node_id, source_slot_index)
        link_map = {}
        for link in links:
            # link format: [link_id, source_node_id, source_slot, target_node_id, target_slot, type]
            if len(link) >= 4:
                link_map[link[0]] = (str(link[1]), link[2])

        # Build target input lookup: (target_node_id, target_slot) -> (source_node_id, source_slot)
        input_connections = {}
        for link in links:
            if len(link) >= 5:
                input_connections[(link[3], link[4])] = (str(link[1]), link[2])

        api_prompt = {}

        for node in nodes:
            node_id = str(node.get("id"))
            class_type = node.get("type")
            if not class_type:
                continue

            inputs = {}
            node_info = obj_info.get(class_type, {})
            input_defs = node_info.get("input", {})

            # Collect ordered widget input names (required + optional, excluding linked types)
            widget_names = []
            for group_key in ("required", "optional"):
                group = input_defs.get(group_key, {})
                for input_name, input_spec in group.items():
                    # Inputs whose type matches a node output type are link-connected, not widgets
                    if isinstance(input_spec, list) and len(input_spec) > 0:
                        input_type = input_spec[0]
                        # Widget types are primitives or lists (combos); skip connectable types
                        if isinstance(input_type, str) and input_type.isupper() and input_type not in (
                            "STRING", "INT", "FLOAT", "BOOLEAN", "COMBO",
                        ):
                            continue
                    widget_names.append(input_name)

            # Map widgets_values positionally to input names
            widgets_values = node.get("widgets_values", [])
            for i, value in enumerate(widgets_values):
                if i < len(widget_names):
                    inputs[widget_names[i]] = value

            # Overlay link connections (these override widget values)
            node_inputs = node.get("inputs", [])
            for slot_idx, node_input in enumerate(node_inputs):
                link_id = node_input.get("link")
                if link_id is not None and link_id in link_map:
                    source_node_id, source_slot = link_map[link_id]
                    input_name = node_input.get("name", f"input_{slot_idx}")
                    inputs[input_name] = [source_node_id, source_slot]

            api_prompt[node_id] = {
                "class_type": class_type,
                "inputs": inputs,
            }

        return api_prompt

    def _ensure_output_nodes(self, prompt):
        """Inject a PreviewAny output node if the workflow has none.

        Finds leaf nodes (nodes whose outputs are not consumed by any input)
        and attaches PreviewAny to the first one found. Skips injection if
        PreviewAny is not registered on this server.
        """
        obj_info = self._get_object_info_cached()

        has_output = any(
            obj_info.get(node.get("class_type"), {}).get("output_node", False)
            for node in prompt.values()
            if isinstance(node, dict) and "class_type" in node
        )
        if has_output:
            return prompt

        if "PreviewAny" not in obj_info:
            return prompt  # Can't auto-inject; let it fail naturally

        # Find leaf nodes: nodes not referenced as a source in any input
        consumed_ids = set()
        for node in prompt.values():
            if isinstance(node, dict):
                for val in node.get("inputs", {}).values():
                    if isinstance(val, list) and len(val) == 2:
                        consumed_ids.add(str(val[0]))

        leaf_id = None
        for nid, node in prompt.items():
            if nid not in consumed_ids and isinstance(node, dict) and "class_type" in node:
                leaf_id = nid

        if leaf_id:
            auto_id = f"_auto_preview_{leaf_id}"
            prompt = dict(prompt)  # Shallow copy to avoid mutating caller's dict
            prompt[auto_id] = {
                "class_type": "PreviewAny",
                "inputs": {"source": [leaf_id, 0]},
            }

        return prompt


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
