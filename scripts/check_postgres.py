"""Verify real PostgreSQL behavior in a newly created, isolated schema."""

import json
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from lottolab.app import create_app
from lottolab.config import Settings, get_settings
from lottolab.db import Draw, QualityIssue, make_engine, make_session_factory
from lottolab.ingestion import canonical, freeze_dataset, ingest_records
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

root = Path(__file__).resolve().parents[1]
os.chdir(root)
original_url = make_url(os.environ.get("LOTTOLAB_TEST_DATABASE_URL", get_settings().database_url))
if original_url.get_backend_name() != "postgresql" or original_url.host not in {
    "localhost",
    "127.0.0.1",
    "db",
}:
    raise SystemExit("Use a dedicated local PostgreSQL instance for this check.")
schema = "lottolab_check_" + uuid4().hex[:12]
base_engine = make_engine(original_url.render_as_string(hide_password=False))
public_exists = inspect(base_engine).has_table("draws", schema="public")
with base_engine.begin() as connection:
    before = connection.scalar(text("SELECT count(*) FROM public.draws")) if public_exists else None
    connection.execute(text(f'CREATE SCHEMA "{schema}"'))
schema_url = original_url.update_query_dict({"options": f"-csearch_path={schema}"})
old_env = os.environ.get("LOTTOLAB_DATABASE_URL")
os.environ["LOTTOLAB_DATABASE_URL"] = schema_url.render_as_string(hide_password=False)
get_settings.cache_clear()
engine = None
report = {"postgres_migrations": "PENDING", "public_draws_before": before}
try:
    command.upgrade(Config("alembic.ini"), "head")
    command.upgrade(Config("alembic.ini"), "head")
    report["postgres_migrations"] = "PASS"
    engine = make_engine(schema_url.render_as_string(hide_password=False))
    factory = make_session_factory(engine)
    data_dir = root / ".local" / "integration" / schema
    sample = {
        "lottery": "ssq",
        "issue": "2026105",
        "draw_date": "2026-09-10",
        "main_numbers": [2, 4, 13, 14, 15, 30],
        "special_numbers": [8],
    }

    def add(db, rows, lottery="ssq"):
        return ingest_records(
            db,
            rows,
            lottery=lottery,
            dataset_kind="real",
            source="integration fixture",
            source_url="fixture://postgres",
            raw=canonical(rows),
            data_dir=data_dir,
        )

    with factory() as db:
        assert add(db, [sample])["accepted"] == 1
        assert add(db, [sample])["duplicates"] == 1
        row = db.scalar(select(Draw))
        row.main_numbers = [2, 2, 13, 14, 15, 30]
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("PostgreSQL accepted duplicate numbers")
        version = freeze_dataset(db, "ssq", "real")
        original_numbers = version.draws[0]["special_numbers"][:]
        db.commit()
        assert add(db, [{**sample, "special_numbers": [1]}])["conflicts"] == 1
        dlt = {**sample, "lottery": "dlt", "main_numbers": [1, 2, 3, 4, 35], "special_numbers": [2, 12]}
        assert add(db, [dlt], "dlt")["accepted"] == 1
    settings = Settings(
        _env_file=None,
        data_dir=data_dir,
        allow_local_writes=True,
        admin_token="",
        allowed_hosts="127.0.0.1,testserver",
    )
    client = TestClient(
        create_app(settings, factory), base_url="http://127.0.0.1:8000", client=("127.0.0.1", 55555)
    )
    issue = client.get("/api/v1/quality").json()["items"][0]
    result = client.post(
        f"/api/v1/quality/{issue['id']}/resolve",
        json={
            "action": "accept_incoming",
            "expected_identity_hash": issue["existing_identity_hash"],
            "expected_record_hash": issue["existing_record_hash"],
        },
    )
    assert result.status_code == 200, result.text
    with factory() as db:
        assert db.get(QualityIssue, issue["id"]).resolution["old"]["special_numbers"] == original_numbers
        assert db.scalar(select(Draw).where(Draw.lottery == "ssq")).special_numbers == [1]
        assert version.draws[0]["special_numbers"] == [8]
    report.update(
        number_constraints="PASS",
        idempotence="PASS",
        cross_lottery_keys="PASS",
        audited_resolution="PASS",
        frozen_snapshot="PASS",
    )
finally:
    if engine:
        engine.dispose()
    if old_env is None:
        os.environ.pop("LOTTOLAB_DATABASE_URL", None)
    else:
        os.environ["LOTTOLAB_DATABASE_URL"] = old_env
    get_settings.cache_clear()
    # Only remove the exact schema created by this invocation; never touch public.
    assert schema.startswith("lottolab_check_") and len(schema) == len("lottolab_check_") + 12
    with base_engine.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        after = connection.scalar(text("SELECT count(*) FROM public.draws")) if public_exists else None
    base_engine.dispose()
    assert before == after, "The public dataset changed during this check; inspect concurrent activity."
    report.update(temporary_schema_removed=True, public_draws_after=after)
    (root / ".local").mkdir(exist_ok=True)
    (root / ".local" / "postgres-verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
print(json.dumps(report, ensure_ascii=False, indent=2))
