#!/usr/bin/env python3
"""
AcadAssist Unified Development Launcher (Part 17)
Starts both the FastAPI backend (http://127.0.0.1:8000) and the Vite React frontend (http://localhost:5173).
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"


def main() -> int:
    print("=" * 68)
    print("  AcadAssist — AI-Powered Personalized Academic Study Assistant")
    print("=" * 68)
    print(f"  Project Root : {ROOT_DIR}")
    print("  Backend API  : http://127.0.0.1:8000  (Swagger Docs: /docs)")
    print("  Frontend UI  : http://localhost:5173")
    print("=" * 68)

    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT_DIR))

    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--reload",
    ]

    npm_bin = "npm.cmd" if os.name == "nt" else "npm"
    frontend_cmd = [npm_bin, "run", "dev"]

    processes = []
    try:
        print("\n[1/2] Starting FastAPI Backend on port 8000...")
        backend_proc = subprocess.Popen(backend_cmd, cwd=str(ROOT_DIR), env=env)
        processes.append(backend_proc)
        time.sleep(1.5)

        print("[2/2] Starting Vite Frontend on port 5173...")
        frontend_proc = subprocess.Popen(frontend_cmd, cwd=str(FRONTEND_DIR), env=env)
        processes.append(frontend_proc)

        print("\nBoth services are running. Press Ctrl+C to stop.\n")
        while True:
            for p in processes:
                if p.poll() is not None:
                    return p.returncode or 0
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nShutting down AcadAssist services...")
    finally:
        for p in processes:
            if p.poll() is None:
                try:
                    if os.name == "nt":
                        p.terminate()
                    else:
                        p.send_signal(signal.SIGTERM)
                except Exception:
                    pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
