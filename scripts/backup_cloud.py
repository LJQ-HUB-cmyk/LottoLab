"""Read-only cloud backup with a verified restore into a separate local database."""

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values
from lottolab import __version__
from lottolab.cloud import postgres_url
from lottolab.db import make_engine
from lottolab.transfer import transfer_database
from sqlalchemy.engine import URL, Engine

ROOT = Path(__file__).resolve().parents[1]


def backup_database(source: Engine, output_root: Path, *, project_dir: Path = ROOT) -> Path:
    """Keep the source read-only; both destinations are newly created local files."""
    directory = output_root / (datetime.now(UTC).strftime("cloud-%Y%m%dT%H%M%SZ-") + uuid4().hex[:8])
    directory.mkdir(parents=True, mode=0o700)
    backup_path = directory / "lottolab.db"
    restore_path = directory / "restore-check.db"
    backup = make_engine(URL.create("sqlite", database=str(backup_path.resolve())).render_as_string())
    restored = make_engine(URL.create("sqlite", database=str(restore_path.resolve())).render_as_string())
    try:
        # Cloud snapshots must be embedded in the source database. There is no
        # fallback to this computer's unrelated raw directory.
        options = {"raw_dir": directory / "absent-raw", "project_dir": project_dir}
        report = transfer_database(source, backup, **options, apply=True)
        replay = transfer_database(backup, restored, **options, apply=True)
        if replay["fingerprints"] != report["fingerprints"]:
            raise ValueError("备份恢复后的数据指纹不一致")
    finally:
        backup.dispose()
        restored.dispose()
    files = {}
    for path in (backup_path, restore_path):
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise ValueError("备份数据库完整性校验失败")
        files[path.name] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
    manifest = {
        **report,
        "version": __version__,
        "created_at": datetime.now(UTC).isoformat(),
        "source_access": "read_only_snapshot",
        "restore_verification": "PASS",
        "files": files,
        "credentials_included": False,
    }
    path = directory / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-env", type=Path, default=ROOT / ".env.cloud.local")
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".local/backups")
    args = parser.parse_args()
    source = None
    try:
        if not args.source_env.is_file():
            raise ValueError("私有云配置文件不存在")
        values = dotenv_values(args.source_env)
        source = make_engine(postgres_url(values.get("LOTTOLAB_DATABASE_URL") or ""), pooled=False)
        manifest = backup_database(source, args.output_dir)
        print(json.dumps({"status": "PASS", "manifest": str(manifest)}, ensure_ascii=False))
    except Exception as exc:
        # Connection errors and SQL exceptions can contain private source details.
        raise SystemExit(
            f"云备份未完成（{type(exc).__name__}）；请检查连接、迁移版本及是否存在运行任务。来源未写入。"
        ) from None
    finally:
        if source is not None:
            source.dispose()


if __name__ == "__main__":
    main()
