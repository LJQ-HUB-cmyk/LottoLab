"""Run the pinned Vercel CLI in the project, with private local credential storage."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    entrypoint = root / ".local/cloud-cli/node_modules/vercel/dist/vc.js"
    node = shutil.which("node")
    if entrypoint.is_file() and node:
        # Invoke Node directly: Windows .cmd shims reinterpret URL metacharacters.
        prefix = [node, str(entrypoint)]
    else:
        pnpm = shutil.which("pnpm")
        if os.name == "nt" or not pnpm:
            raise SystemExit(
                "需要 Node 和项目内 Vercel CLI；请先运行 "
                "pnpm --dir .local/cloud-cli add --save-exact --ignore-scripts vercel@59.16.0"
            )
        prefix = [pnpm, "dlx", "vercel@59.16.0"]
    config_dir = root / ".local/vercel-config"
    config_dir.mkdir(parents=True, exist_ok=True)
    arguments = sys.argv[1:] or ["--help"]
    environment = {**os.environ, "VERCEL_TELEMETRY_DISABLED": "1"}
    separator = arguments.index("--") if "--" in arguments else len(arguments)
    cli_arguments = [
        *arguments[:separator],
        "--global-config",
        str(config_dir),
        "--cwd",
        str(root),
        *arguments[separator:],
    ]
    result = subprocess.run(
        # Some integration subcommands slice argv positionally; keep them first.
        [*prefix, *cli_arguments],
        cwd=root,
        env=environment,
        check=False,
    )
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
