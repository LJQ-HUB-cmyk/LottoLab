"""Vercel FastAPI entrypoint. Local development uses lottolab.app:create_app."""

import sys
from pathlib import Path

# Vercel installs runtime dependencies without installing this editable project.
# Spawned calculation processes inherit this source path as well.
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from lottolab.app import create_app  # noqa: E402
from lottolab.cloud import vercel_settings  # noqa: E402

app = create_app(vercel_settings())
