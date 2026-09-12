import hashlib
import json
import sqlite3

from lottolab.db import RawSnapshot, make_engine
from lottolab.transfer import transfer_database
from sqlalchemy import event, func, select

from scripts.backup_cloud import backup_database

from .test_transfer import ROOT, seed


def test_cloud_backup_restores_without_source_writes_or_external_raw_files(
    session_factory, tmp_path, raw_draw
):
    seed(session_factory, tmp_path, raw_draw)
    source = make_engine(f"sqlite:///{(tmp_path / 'cloud-source.db').as_posix()}")
    try:
        original = transfer_database(
            session_factory.kw["bind"],
            source,
            raw_dir=tmp_path / "raw",
            project_dir=ROOT,
            apply=True,
        )

        @event.listens_for(source, "before_cursor_execute")
        def reject_source_writes(_connection, _cursor, statement, _params, _context, _many):
            assert not statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "DROP"))

        manifest_path = backup_database(source, tmp_path / "private-backups")
        manifest = json.loads(manifest_path.read_text())
        assert manifest["restore_verification"] == "PASS"
        assert manifest["fingerprints"] == original["fingerprints"]
        assert manifest["rows"]["jobs"] == 2
        assert manifest["rows"]["quality_issues"] == 2
        assert not manifest["credentials_included"]
        for name, info in manifest["files"].items():
            path = manifest_path.parent / name
            assert hashlib.sha256(path.read_bytes()).hexdigest() == info["sha256"]
            with sqlite3.connect(path) as db:
                assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
                jobs = db.execute("SELECT status, result, error FROM jobs ORDER BY status").fetchall()
                assert jobs[0][0] == "completed" and "historical-evidence" in jobs[0][1]
                assert jobs[1][0] == "failed" and jobs[1][2] == "previous failure retained"
        with source.connect() as db:
            assert db.scalar(select(func.count()).select_from(RawSnapshot)) == 2
        second = backup_database(source, tmp_path / "private-backups")
        assert second.parent != manifest_path.parent
        assert json.loads(second.read_text())["fingerprints"] == original["fingerprints"]
        assert manifest_path.is_file()
    finally:
        source.dispose()
