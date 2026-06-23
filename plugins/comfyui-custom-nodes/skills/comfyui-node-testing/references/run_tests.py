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

# Import shared configuration
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import env_config
except ImportError:
    # Handle direct/nested invocation if sys.path isn't resolved
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"))
    import env_config

TESTS_DIR = env_config.TESTS_DIR
COMFYUI_ROOT = env_config.COMFYUI_ROOT
PYTHON_EXE = env_config.VENV_PYTHON
COMFYUI_MAIN = os.path.join(COMFYUI_ROOT, "main.py")

_server_process = None
_server_log = None


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
    global _server_process, _server_log
    if is_server_running():
        print("[INFO] ComfyUI server already running on port 8188")
        return None

    print("[INFO] Starting ComfyUI server...")
    creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    
    log_path = os.path.join(TESTS_DIR, "comfyui_server.log")
    _server_log = open(log_path, "w", encoding="utf-8", errors="replace")

    server_env = os.environ.copy()
    server_env.pop("COMFYUI_TESTING", None)
    server_env.pop("PYTEST_CURRENT_TEST", None)

    # Determine device mode: GPU by default, CPU only if forced or no CUDA
    comfy_args = [PYTHON_EXE, COMFYUI_MAIN, "--listen", "127.0.0.1", "--port", "8188"]

    force_cpu = os.environ.get("COMFYUI_TEST_FORCE_CPU", "") == "1"
    if force_cpu:
        comfy_args.append("--cpu")
        print("[INFO] Device: CPU (COMFYUI_TEST_FORCE_CPU=1)")
    else:
        # Probe CUDA via the venv python (system python may lack torch)
        try:
            probe = subprocess.run(
                [PYTHON_EXE, "-c", "import torch; print(torch.cuda.is_available())"],
                capture_output=True, text=True, timeout=15,
            )
            has_cuda = probe.stdout.strip() == "True"
        except Exception:
            has_cuda = False

        if has_cuda:
            print("[INFO] Device: GPU (CUDA available)")
        else:
            comfy_args.append("--cpu")
            print("[INFO] Device: CPU (no CUDA detected)")

    _server_process = subprocess.Popen(
        comfy_args,
        cwd=COMFYUI_ROOT,
        stdout=_server_log,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
        env=server_env,
    )
    atexit.register(stop_comfyui_server)

    print("   Waiting for server readiness...", end="", flush=True)
    for i in range(60):
        if is_server_running():
            print(f" ready! ({i + 1}s)")
            return _server_process
        time.sleep(1)
        print(".", end="", flush=True)

    print("\n[ERROR] Server failed to start within 60 seconds")
    stop_comfyui_server()
    sys.exit(1)


def stop_comfyui_server():
    """Gracefully terminate the backgrounded server."""
    global _server_process, _server_log
    if _server_process is None:
        return
    print("\n[INFO] Stopping ComfyUI server...")
    if sys.platform == "win32":
        _server_process.terminate()
    else:
        try:
            os.killpg(os.getpgid(_server_process.pid), signal.SIGTERM)
        except ProcessLookupError:
            _server_process.terminate()
    _server_process.wait(timeout=10)
    _server_process = None

    if _server_log is not None:
        _server_log.close()
        _server_log = None


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
    print(f"\n[TESTS] Executing: {' '.join(pytest_args)}")

    try:
        result = subprocess.run(pytest_args, env=os.environ)
        return result.returncode
    finally:
        stop_comfyui_server()


if __name__ == "__main__":
    sys.exit(main())

