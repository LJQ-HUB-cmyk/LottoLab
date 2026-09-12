import gzip

import pytest
from lottolab.db import RawSnapshot
from lottolab.snapshots import save_snapshot, snapshot_bytes
from sqlalchemy import func, select


def test_database_snapshots_deduplicate_and_verify_original_bytes(session_factory):
    raw = "原始公开数据\n".encode() * 100
    with session_factory() as db:
        checksum = save_snapshot(db, raw, None)
        db.commit()
        assert save_snapshot(db, raw, None) == checksum
        db.commit()
        assert db.scalar(select(func.count()).select_from(RawSnapshot)) == 1
        stored = db.get(RawSnapshot, checksum)
        assert stored.raw_size == len(raw)
        assert len(stored.content) < len(raw)
        assert snapshot_bytes(stored) == raw


@pytest.mark.parametrize("corruption", ["hash", "size", "compression", "deflate"])
def test_database_snapshot_corruption_is_detected(session_factory, corruption):
    with session_factory() as db:
        checksum = save_snapshot(db, b"original", None)
        db.commit()
        stored = db.get(RawSnapshot, checksum)
        if corruption == "hash":
            stored.content = gzip.compress(b"tampered")
        elif corruption == "size":
            stored.raw_size = 1
        elif corruption == "deflate":
            # A valid gzip header followed by the forbidden DEFLATE block type.
            stored.content = gzip.compress(b"original")[:10] + b"\x07" + b"\x00" * 8
        else:
            stored.content = b"broken gzip"
        db.commit()
        with pytest.raises(ValueError):
            save_snapshot(db, b"original", None)


def test_existing_filesystem_snapshot_is_never_overwritten(session_factory, tmp_path):
    with session_factory() as db:
        checksum = save_snapshot(db, b"original", tmp_path)
        path = tmp_path / f"{checksum}.snapshot"
        path.write_bytes(b"preserve damaged file for investigation")
        with pytest.raises(ValueError):
            save_snapshot(db, b"original", tmp_path)
        assert path.read_bytes() == b"preserve damaged file for investigation"
