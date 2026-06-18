#!/usr/bin/env python
"""
Universal ComfyUI Custom Node Test Runner.

Handles working directory isolation, cross-platform venv detection,
and auto-manages a ComfyUI server lifecycle for integration tests.

Usage (from the custom node root):
    python tests/run_tests.py --all           # all tests
    python tests/run_tests.py unit/           # unit only
    python tests/run_tests.py integration/    # integration only
    python tests/run_tests.py -m unit         # via marker
"""

import os
import sys
import subprocess
import time
import signal
import atexit

# Flag for code paths that need to know they're under test
os.environ["COMFYUI_TESTING"] = "1"

# ---------------------------------------------------------------------------
# Path routing
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Works whether invoked from repo root or inside tests/
TESTS_DIR = SCRIPT_DIR if SCRIPT_DIR.endswith("tests") else os.path.join(SCRIPT_DIR, "tests")
COMFYUI_ROOT = os.path.abspath(os.path.join(TESTS_DIR, "..", ".."))
COMFYUI_MAIN = os.path.join(COMFYUI_ROOT, "main.py")

# Cross-platform venv resolution
if os.name == "nt":
    PYTHON_EXE = os.path.join(COMFYUI_ROOT, "venv", "Scripts", "python.exe")
else:
    PYTHON_EXE = os.path.join(COMFYUI_ROOT, "venv", "bin", "python")

_server_process = None


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------

def is_server_running(host="127.0.0.1", port=8188):
    """Check if ComfyUI server port is active."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False


def start_comfyui_server():
    """Background a managed ComfyUI instance for integration tests."""
    global _server_process
    if is_server_running():
        print("✓ ComfyUI server already running on port 8188")
        return None

    print("🚀 Starting ComfyUI server...")
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    _server_process = subprocess.Popen(
        [PYTHON_EXE, COMFYUI_MAIN, "--listen", "127.0.0.1", "--port", "8188"],
        cwd=COMFYUI_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )
    atexit.register(stop_comfyui_server)

    print("   Waiting for server readiness...", end="", flush=True)
    for i in range(60):
        if is_server_running():
            print(f" ready! ({i + 1}s)")
            return _server_process
        time.sleep(1)
        print(".", end="", flush=True)

    print("\n✗ Server failed to start within 60 seconds")
    stop_comfyui_server()
    sys.exit(1)


def stop_comfyui_server():
    """Gracefully terminate the backgrounded server."""
    global _server_process
    if _server_process is None:
        return
    print("\n🛑 Stopping ComfyUI server...")
    if sys.platform == "win32":
        _server_process.terminate()
    else:
        try:
            os.killpg(os.getpgid(_server_process.pid), signal.SIGTERM)
        except ProcessLookupError:
            _server_process.terminate()
    _server_process.wait(timeout=10)
    _server_process = None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    running_integration = "-m" not in args or "integration" in args
    running_unit_only = "-m" in args and "unit" in args and "integration" not in args

    if running_integration and not running_unit_only:
        start_comfyui_server()

    # Isolate to tests/ so the local pytest.ini wins over ComfyUI's root config
    os.chdir(TESTS_DIR)

    # Filter out --all if present, as it is a runner-specific flag to run all tests
    # (which pytest does by default when no specific path/marker is given)
    pytest_args = [PYTHON_EXE, "-m", "pytest"] + [a for a in args if a != "--all"]
    print(f"\n📋 Executing: {' '.join(pytest_args)}")

    try:
        result = subprocess.run(pytest_args, env=os.environ)
        return result.returncode
    finally:
        stop_comfyui_server()


if __name__ == "__main__":
    sys.exit(main())
