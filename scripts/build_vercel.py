"""Build the web client without connecting to or migrating a database."""

import json
import shutil
import subprocess
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    frontend = root / "frontend"
    package = json.loads((frontend / "package.json").read_text(encoding="utf-8"))
    manager = package["packageManager"]
    pnpm = shutil.which("pnpm")
    if pnpm and subprocess.check_output([pnpm, "--version"], text=True).strip() == manager.split("@")[-1]:
        launcher = [pnpm]
    else:
        # Vercel's Node environment includes npx; use the pinned package manager.
        npx = shutil.which("npx")
        if npx is None:
            raise SystemExit("Install the pinned pnpm version or Node.js 24 with npx")
        launcher = [npx, "--yes", manager]
    for args in (["install", "--frozen-lockfile"], ["build"]):
        subprocess.run([*launcher, *args], cwd=frontend, check=True)
    if not (frontend / "dist" / "index.html").is_file():
        raise SystemExit("Frontend build did not produce index.html")
    print("Frontend ready; no database changes performed during build.")


if __name__ == "__main__":
    main()
