"""Root runner for Bitget OctaCore - delegates execution to backend/main.py."""

import os
import sys

# Ensure UTF-8 stdout on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure AppLocker/Application Control DLL blocking on pyarrow does not crash pandas
try:
    import pyarrow  # noqa: F401
except (ImportError, Exception):
    sys.modules["pyarrow"] = None

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Switch working directory to backend so all relative paths and local files resolve identically
os.chdir(BACKEND_DIR)

if __name__ == "__main__":
    import importlib.util
    backend_main_path = os.path.join(BACKEND_DIR, "main.py")
    spec = importlib.util.spec_from_file_location("backend_main_module", backend_main_path)
    backend_main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend_main)
    backend_main.main()
