"""Real PostgreSQL checks; the CI service provides the explicit local test URL."""

import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from threading import Barrier, Event
from uuid import uuid4

import pytest
from lottolab.app import create_app
from lottolab.db import Base, Job, RawSnapshot, make_engine, make_session_factory
from lottolab.snapshots import snapshot_bytes
from lottolab.transfer import transfer_database
from sqlalchemy import event, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from .test_cloud import TOKEN, cloud_client
from .test_transfer import seed

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def postgres_engine():
    value = os.environ.get("LOTTOLAB_TEST_DATABASE_URL")
    if not value:
        pytest.skip("LOTTOLAB_TEST_DATABASE_URL is not set; requires dedicated local PostgreSQL")
    url = make_url(value)
    if url.get_backend_name() != "postgresql" or url.host not in {"localhost", "127.0.0.1", "db"}:
        pytest.fail("PostgreSQL integration tests require a dedicated local service")
    schema = "lottolab_cloud_test_" + uuid4().hex
    base = make_engine(value, pooled=False)
    engine = None
    try:
        with base.begin() as db:
            db.execute(text(f'CREATE SCHEMA "{schema}"'))
        # A non-UTC server session detects accidental reinterpretation of SQLite timestamps.
        scoped = url.update_query_dict({"options": f"-csearch_path={schema} -cTimeZone=Asia/Shanghai"})
        engine = make_engine(scoped.render_as_string(hide_password=False), pooled=False)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        # The schema identifier is generated here; no existing schema is removed.
        with base.begin() as db:
            db.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        base.dispose()


def test_cloud_transfer_and_request_execution_on_postgres(
    postgres_engine, session_factory, tmp_path, raw_draw
):
    seed(session_factory, tmp_path, raw_draw)
    options = {"raw_dir": tmp_path / "raw", "project_dir": ROOT}
    source = session_factory.kw["bind"]
    preview = transfer_database(source, postgres_engine, **options)
    assert preview["status"] == "DRY_RUN" and inspect(postgres_engine).get_table_names() == []
    report = transfer_database(source, postgres_engine, **options, apply=True)
    assert report["status"] == "PASS" and report["fingerprints"] == preview["fingerprints"]
    assert isinstance(postgres_engine.pool, NullPool)
    restored = make_engine(f"sqlite:///{(tmp_path / 'restored.db').as_posix()}")
    try:
        round_trip = transfer_database(
            postgres_engine, restored, raw_dir=tmp_path / "absent", project_dir=ROOT, apply=True
        )
        assert round_trip["fingerprints"] == report["fingerprints"]
    finally:
        restored.dispose()
    factory = make_session_factory(postgres_engine)
    client, settings = cloud_client(factory, tmp_path / "ephemeral-runtime")
    headers = {"X-Admin-Token": TOKEN}
    assert client.get("/api/v1/jobs").status_code == 403
    job = client.post("/api/v1/simulations", json={"iterations": 1000}, headers=headers).json()
    assert job["status"] == "completed" and job["result"]["iterations"] == 1000
    demo = client.post("/api/v1/datasets/demo", json={"count": 100}, headers=headers).json()
    assert demo["status"] == "completed" and demo["result"]["accepted"] == 100
    assert not settings.data_dir.exists()
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(RawSnapshot)) == 3
        assert all(snapshot_bytes(row) for row in db.scalars(select(RawSnapshot)))
        assert db.get(Job, job["id"]).result == job["result"]
    # Another API instance, without files or a worker, reads the same persisted result.
    restarted, _ = cloud_client(factory, tmp_path / "another-instance")
    assert restarted.get(f"/api/v1/jobs/{job['id']}", headers=headers).json()["result"] == job["result"]


def test_independent_instances_serialize_cloud_admission(postgres_engine, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from lottolab.worker import run_request_job

    Base.metadata.create_all(postgres_engine)
    factory = make_session_factory(postgres_engine)
    first, settings = cloud_client(factory, tmp_path)
    second = TestClient(create_app(settings, factory), base_url="https://lab.example")
    release = Event()
    start = Barrier(3)

    def hold_execution(*args):
        assert release.wait(15), "Concurrent admission did not complete"
        run_request_job(*args)

    def widen_race(_connection, _cursor, statement, _params, _context, _many):
        # Delay after reading the active count. An instance-local lock cannot protect this race.
        if "count(*)" in statement and "jobs.status IN" in statement:
            time.sleep(0.2)

    def submit(client):
        start.wait(10)
        return client.post("/api/v1/simulations", json={"iterations": 1000}, headers={"X-Admin-Token": TOKEN})

    monkeypatch.setattr("lottolab.app.run_request_job", hold_execution)
    event.listen(postgres_engine, "after_cursor_execute", widen_race)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(submit, client) for client in (first, second)]
            try:
                start.wait(10)
                done, pending = wait(futures, timeout=10, return_when=FIRST_COMPLETED)
                assert len(done) == len(pending) == 1, "Both instances admitted a task or admission stalled"
                assert next(iter(done)).result().status_code == 429
                with factory() as db:
                    assert db.scalar(select(func.count()).select_from(Job)) == 1
            finally:
                release.set()
            responses = [future.result(timeout=15) for future in futures]
            completed = next(response.json() for response in responses if response.status_code == 202)
            assert completed["status"] == "completed"
    finally:
        event.remove(postgres_engine, "after_cursor_execute", widen_race)
