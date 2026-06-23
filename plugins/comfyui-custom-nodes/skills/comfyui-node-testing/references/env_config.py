"""
Shared environment configuration and path resolution for ComfyUI custom node testing.
Loads local environment variables from .env and .env.local files,
and resolves critical paths (ComfyUI root, virtual environment python executable).
"""

import os
import sys

def load_env(filepath):
    """Simple parser to load a .env file into os.environ if it exists."""
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Load environment overrides from local files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Works whether invoked from repo root, tests/, or tests/diagnostics/
TESTS_DIR = SCRIPT_DIR if SCRIPT_DIR.endswith("tests") else os.path.join(SCRIPT_DIR, "tests")
if not os.path.isdir(TESTS_DIR):
    TESTS_DIR = SCRIPT_DIR

load_env(os.path.join(TESTS_DIR, ".env"))
load_env(os.path.join(TESTS_DIR, ".env.local"))

# 1. Resolve ComfyUI Root Directory
COMFYUI_ROOT = os.environ.get("COMFYUI_TEST_COMFY_ROOT")
if not COMFYUI_ROOT:
    # Default fallback: navigate up from custom_nodes/<node_name>/tests/
    # standard path: custom_nodes/<node_name>/tests -> custom_nodes/<node_name> -> custom_nodes -> ComfyUI
    default_root = os.path.abspath(os.path.join(TESTS_DIR, "..", "..", ".."))
    if os.path.isdir(default_root) and os.path.isfile(os.path.join(default_root, "main.py")):
        COMFYUI_ROOT = default_root
    else:
        # Fallback to two levels up (sometimes custom_nodes are directly under root in simplified dev setups)
        alt_root = os.path.abspath(os.path.join(TESTS_DIR, "..", ".."))
        if os.path.isdir(alt_root) and os.path.isfile(os.path.join(alt_root, "main.py")):
            COMFYUI_ROOT = alt_root
        else:
            print("[ERROR] Could not automatically locate ComfyUI root directory.")
            print("[INFO] Please create a 'tests/.env.local' file and define:")
            print("       COMFYUI_TEST_COMFY_ROOT=/path/to/ComfyUI")
            sys.exit(1)
    os.environ["COMFYUI_TEST_COMFY_ROOT"] = COMFYUI_ROOT

# 2. Resolve Virtual Environment Python Executable
VENV_PYTHON = os.environ.get("COMFYUI_TEST_VENV_PYTHON")
if not VENV_PYTHON:
    # Compile a list of candidate venv paths to check (both ComfyUI-level and project-local)
    candidates = []
    if os.name == "nt":
        candidates.append(os.path.join(COMFYUI_ROOT, "venv", "Scripts", "python.exe"))
        candidates.append(os.path.join(TESTS_DIR, "..", ".venv", "Scripts", "python.exe"))
        candidates.append(os.path.join(TESTS_DIR, "..", "venv", "Scripts", "python.exe"))
    else:
        candidates.append(os.path.join(COMFYUI_ROOT, "venv", "bin", "python"))
        candidates.append(os.path.join(TESTS_DIR, "..", ".venv", "bin", "python"))
        candidates.append(os.path.join(TESTS_DIR, "..", "venv", "bin", "python"))
    
    # Filter candidates: path must exist and pytest must be importable
    import subprocess
    resolved = None
    for path in candidates:
        if os.path.isfile(path):
            try:
                # Fast check to ensure pytest is importable inside the venv
                res = subprocess.run(
                    [path, "-c", "import pytest"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3
                )
                if res.returncode == 0:
                    resolved = path
                    break
            except Exception:
                continue
                
    if resolved:
        VENV_PYTHON = resolved
    else:
        # Fallback to sys.executable if no valid venv with pytest is found
        VENV_PYTHON = sys.executable
    os.environ["COMFYUI_TEST_VENV_PYTHON"] = VENV_PYTHON
