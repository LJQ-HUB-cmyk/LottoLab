"""Execution metadata shared by every persisted experiment."""

import hashlib
import importlib.metadata
import platform
from pathlib import Path

from . import __version__


def code_fingerprint() -> str:
    hasher = hashlib.sha256()
    for file in sorted(Path(__file__).parent.glob("*.py")):
        hasher.update(file.name.encode())
        hasher.update(file.read_bytes())
    return hasher.hexdigest()


def execution_metadata(rule_version: str) -> dict:
    return {
        "code_fingerprint": code_fingerprint(),
        "rule_version": rule_version,
        "python": platform.python_version(),
        "packages": {
            "lottolab": __version__,
            **{name: importlib.metadata.version(name) for name in ("numpy", "scipy", "scikit-learn")},
        },
    }
