"""Foreground-managed local launcher. Its children stop when this window closes."""

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class WindowsProcessGroup:
    """Close the entire API/worker process tree if the launcher window closes."""

    def __init__(self):
        self.handle = None
        if os.name != "nt":
            return
        import ctypes
        from ctypes import wintypes

        class BasicLimits(ctypes.Structure):
            _fields_ = [
                ("process_time", ctypes.c_int64),
                ("job_time", ctypes.c_int64),
                ("flags", wintypes.DWORD),
                ("minimum_working_set", ctypes.c_size_t),
                ("maximum_working_set", ctypes.c_size_t),
                ("active_processes", wintypes.DWORD),
                ("affinity", ctypes.c_size_t),
                ("priority", wintypes.DWORD),
                ("scheduling", wintypes.DWORD),
            ]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [
                ("basic", BasicLimits),
                ("io_counters", ctypes.c_uint64 * 6),
                ("process_memory", ctypes.c_size_t),
                ("job_memory", ctypes.c_size_t),
                ("peak_process_memory", ctypes.c_size_t),
                ("peak_job_memory", ctypes.c_size_t),
            ]

        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        self.kernel.SetInformationJobObject.restype = wintypes.BOOL
        self.kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.kernel.AssignProcessToJobObject.restype = wintypes.BOOL
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel.CloseHandle.restype = wintypes.BOOL
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(
            self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
        ):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def add(self, process):
        if self.handle and not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
            import ctypes

            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def main():
    parser = argparse.ArgumentParser(description="Start the LottoLab local workbench")
    parser.add_argument("--sqlite", action="store_true", help="Use a separate local SQLite database")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--check", action="store_true", help="Verify launcher requirements without starting services"
    )
    args = parser.parse_args()
    os.chdir(ROOT)
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    from lottolab.config import get_settings
    from lottolab.domain import DISCLAIMER

    if args.check:
        assert (ROOT / "frontend" / "dist" / "index.html").is_file(), "Build the frontend first"
        print("Launcher requirements: PASS")
        return
    if not (ROOT / ".env").exists():
        subprocess.run([sys.executable, "scripts/bootstrap_env.py"], check=True)
    get_settings.cache_clear()
    settings = get_settings()
    url = f"http://127.0.0.1:{args.port}"
    local_http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with local_http.open(url + "/api/v1/health", timeout=2) as response:
            existing = json.load(response)
        if existing.get("disclaimer") == DISCLAIMER:
            if not existing.get("worker_ready"):
                raise SystemExit(
                    "The API is running but its worker is offline. Stop its launcher and restart, "
                    "or start the matching worker with python -m lottolab.worker."
                )
            if args.sqlite and existing.get("database") != "sqlite":
                raise SystemExit(
                    "This port is serving PostgreSQL. Use --port to open a separate SQLite instance."
                )
            print(f"LottoLab is already running: {url}")
            if not args.no_browser:
                webbrowser.open(url)
            return
    except (OSError, ValueError, urllib.error.URLError):
        pass
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", args.port))
        except OSError:
            raise SystemExit(
                f"Port {args.port} is in use. Choose another port; no existing service was stopped."
            ) from None
    env = os.environ.copy()
    env["LOTTOLAB_ALLOW_LOCAL_WRITES"] = "true"
    env["LOTTOLAB_ALLOWED_ORIGINS"] = f"http://127.0.0.1:{args.port},http://localhost:{args.port}"
    env["LOTTOLAB_ALLOWED_HOSTS"] = "localhost,127.0.0.1"
    if args.sqlite:
        env["LOTTOLAB_DATABASE_URL"] = "sqlite:///./.local/lottolab.db"
    elif settings.database_url.startswith("postgresql"):
        from sqlalchemy.engine import make_url

        db_url = make_url(settings.database_url)
        if db_url.host not in ("localhost", "127.0.0.1") or db_url.port != 55432:
            raise SystemExit(
                "This launcher manages only the project's local database; use the deployment runbook for other databases."
            )
        try:
            ready = (
                subprocess.run(
                    ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15
                ).returncode
                == 0
            )
            if not ready:
                print("Starting Docker Desktop...", flush=True)
                subprocess.run(["docker", "desktop", "start", "--timeout", "45"], check=True, timeout=55)
            subprocess.run(["docker", "compose", "up", "-d", "--wait", "db"], check=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as exc:
            raise SystemExit(
                "Docker is unavailable. Start Docker Desktop, or use --sqlite for the separate local database. "
                f"({type(exc).__name__})"
            ) from None
    if not (ROOT / "frontend" / "dist" / "index.html").is_file():
        raise SystemExit("Frontend is not built. Run pnpm install and pnpm build in frontend first.")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=True)
    local = ROOT / ".local"
    local.mkdir(exist_ok=True)
    children = []
    handles = []
    process_group = WindowsProcessGroup()
    stopping = False

    def stop(_signal=None, _frame=None):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        for name, command in (
            ("api", ["-m", "lottolab.cli", "serve", "--port", str(args.port)]),
            ("worker", ["-m", "lottolab.worker"]),
        ):
            handle = (local / f"{name}.log").open("ab")
            handles.append(handle)
            child = subprocess.Popen(
                [sys.executable, *command],
                cwd=ROOT,
                env=env,
                stdout=handle,
                stderr=handle,
                creationflags=creationflags,
            )
            children.append(child)
            process_group.add(child)
        for _ in range(60):
            if any(child.poll() is not None for child in children):
                raise RuntimeError("A service exited during startup; inspect .local/api.log and worker.log")
            try:
                with local_http.open(url + "/api/v1/health", timeout=1) as response:
                    health = json.load(response)
                    if response.status == 200 and health.get("worker_ready") and health.get("can_write"):
                        break
            except (OSError, ValueError):
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("API startup failed; inspect .local/api.log")
        print(
            f"LottoLab is ready: {url} ({health['database']})\n"
            "Keep this window open. Press Ctrl+C to stop these local services.",
            flush=True,
        )
        if not args.no_browser:
            webbrowser.open(url)
        while not stopping:
            if any(child.poll() is not None for child in children):
                raise RuntimeError("A service stopped unexpectedly; inspect .local/api.log and worker.log")
            time.sleep(0.5)
    finally:
        process_group.close()
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill()
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    main()
