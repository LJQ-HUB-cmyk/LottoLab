"""Create a private local environment without replacing existing settings."""

import argparse
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--postgres", action="store_true", help="Use local Compose PostgreSQL instead of SQLite")
args = parser.parse_args()
path = root / ".env"
if path.exists():
    print("Existing .env preserved.")
else:
    password = secrets.token_hex(24)
    token = secrets.token_hex(32)
    text = (root / ".env.example").read_text(encoding="utf-8")
    text = text.replace("POSTGRES_PASSWORD=\n", f"POSTGRES_PASSWORD={password}\n")
    text = text.replace("LOTTOLAB_ADMIN_TOKEN=\n", f"LOTTOLAB_ADMIN_TOKEN={token}\n")
    if args.postgres:
        text = text.replace(
            "sqlite:///./.local/lottolab.db",
            f"postgresql+psycopg://lottolab:{password}@127.0.0.1:55432/lottolab",
        )
    path.write_text(text, encoding="utf-8", newline="\n")
    print("Local .env created; credentials were not printed.")
