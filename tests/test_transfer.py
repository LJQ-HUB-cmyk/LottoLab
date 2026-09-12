from pathlib import Path

import pytest
from lottolab.db import Job, RawSnapshot, make_engine
from lottolab.ingestion import canonical, freeze_dataset, ingest_records
from lottolab.transfer import transfer_database
from sqlalchemy import event, func, inspect, select

ROOT = Path(__file__).resolve().parents[1]


def seed(factory, tmp_path, raw_draw):
    with factory() as db:
        for rows in (
            [{**raw_draw, "sales": "12345.67", "prizes": {"1": "5000000.00"}}],
            [{**raw_draw, "special_numbers": [1]}, {**raw_draw, "issue": "bad", "main_numbers": [99]}],
        ):
            ingest_records(
                db,
                rows,
                lottery="ssq",
                dataset_kind="real",
                source="migration fixture",
                source_url="fixture://migration",
                raw=canonical(rows),
                data_dir=tmp_path,
            )
        dataset = freeze_dataset(db, "ssq", "real")
        db.add(
            Job(
                kind="backtest",
                lottery="ssq",
                dataset_kind="real",
                status="completed",
                dataset_id=dataset.id,
                params={"seed": 123},
                result={"execution": {"code_fingerprint": "historical-evidence"}, "score": 0.2},
            )
        )
        db.add(
            Job(
                kind="backtest",
                lottery="ssq",
                dataset_kind="real",
                status="failed",
                dataset_id=dataset.id,
                params={"seed": 123},
                error="previous failure retained",
            )
        )
        db.commit()


def test_transfer_preserves_audit_results_ids_and_snapshots_without_source_writes(
    session_factory, tmp_path, raw_draw
):
    seed(session_factory, tmp_path, raw_draw)
    source = session_factory.kw["bind"]
    target = make_engine(f"sqlite:///{(tmp_path / 'cloud.db').as_posix()}")
    restored = make_engine(f"sqlite:///{(tmp_path / 'restored.db').as_posix()}")
    try:
        options = {"raw_dir": tmp_path / "raw", "project_dir": ROOT}
        preview = transfer_database(source, target, **options)
        assert preview["status"] == "DRY_RUN" and inspect(target).get_table_names() == []
        report = transfer_database(source, target, **options, apply=True)
        assert report["status"] == "PASS"
        assert report["rows"] == {
            "draws": 1,
            "ingestion_runs": 2,
            "quality_issues": 2,
            "jobs": 2,
            "dataset_versions": 1,
            "raw_snapshots": 2,
        }
        with session_factory() as db:
            assert db.scalar(select(func.count()).select_from(RawSnapshot)) == 0
            assert db.scalar(select(func.count()).select_from(Job)) == 2
        with pytest.raises(ValueError, match="已有数据"):
            transfer_database(source, target, **options, apply=True)
        second = transfer_database(
            target, restored, raw_dir=tmp_path / "absent-on-new-machine", project_dir=ROOT, apply=True
        )
        assert second["fingerprints"] == report["fingerprints"]
    finally:
        target.dispose()
        restored.dispose()


@pytest.mark.parametrize("problem", ["missing", "corrupt", "running"])
def test_transfer_preflight_leaves_target_empty_on_invalid_source(
    session_factory, tmp_path, raw_draw, problem
):
    seed(session_factory, tmp_path, raw_draw)
    if problem == "missing":
        next((tmp_path / "raw").glob("*.snapshot")).unlink()
    elif problem == "corrupt":
        next((tmp_path / "raw").glob("*.snapshot")).write_bytes(b"corrupt")
    else:
        with session_factory() as db:
            db.scalar(select(Job)).status = "running"
            db.commit()
    target = make_engine(f"sqlite:///{(tmp_path / 'empty.db').as_posix()}")
    try:
        with pytest.raises(ValueError):
            transfer_database(
                session_factory.kw["bind"],
                target,
                raw_dir=tmp_path / "raw",
                project_dir=ROOT,
                apply=True,
            )
        assert inspect(target).get_table_names() == []
    finally:
        target.dispose()


def test_transfer_rolls_back_all_target_writes_if_a_later_table_fails(session_factory, tmp_path, raw_draw):
    seed(session_factory, tmp_path, raw_draw)
    target = make_engine(f"sqlite:///{(tmp_path / 'rollback.db').as_posix()}")

    @event.listens_for(target, "before_cursor_execute")
    def fail_on_jobs(_connection, _cursor, statement, _parameters, _context, _executemany):
        if statement.startswith("INSERT INTO jobs"):
            raise RuntimeError("injected destination failure")

    try:
        with pytest.raises(RuntimeError, match="injected destination failure"):
            transfer_database(
                session_factory.kw["bind"],
                target,
                raw_dir=tmp_path / "raw",
                project_dir=ROOT,
                apply=True,
            )
        assert inspect(target).get_table_names() == []
    finally:
        target.dispose()
