from lottolab.db import Draw, QualityIssue
from lottolab.ingestion import canonical, freeze_dataset, ingest_records
from sqlalchemy import select

from tests.test_api import client_for


def add(db, rows, tmp_path):
    return ingest_records(
        db,
        rows,
        lottery="ssq",
        dataset_kind="real",
        source="fixture",
        source_url="fixture://quality",
        raw=canonical(rows),
        data_dir=tmp_path,
    )


def test_conflict_requires_review_and_revision_preserves_frozen_history(session_factory, raw_draw, tmp_path):
    with session_factory() as db:
        add(db, [raw_draw], tmp_path)
        version = freeze_dataset(db, "ssq", "real")
        frozen_id = version.id
        db.commit()
        assert add(db, [{**raw_draw, "special_numbers": [1], "sales": "5.00"}], tmp_path)["conflicts"] == 1
    client, _ = client_for(session_factory, tmp_path)
    issue = client.get("/api/v1/quality").json()["items"][0]
    assert issue["existing"]["special_numbers"] == [8]
    blocked = client.post("/api/v1/backtests", json={"test_draws": 20})
    assert blocked.status_code == 422 and "未复核冲突" in blocked.text
    stale = {
        "action": "accept_incoming",
        "expected_identity_hash": issue["existing_identity_hash"],
        "expected_record_hash": "0" * 64,
    }
    assert client.post(f"/api/v1/quality/{issue['id']}/resolve", json=stale).status_code == 409
    valid = {**stale, "expected_record_hash": issue["existing_record_hash"]}
    assert client.post(f"/api/v1/quality/{issue['id']}/resolve", json=valid).status_code == 200
    assert client.post(f"/api/v1/quality/{issue['id']}/resolve", json=valid).status_code == 409
    with session_factory() as db:
        draw = db.scalar(select(Draw))
        audit = db.get(QualityIssue, issue["id"])
        assert draw.special_numbers == [1]
        assert audit.resolution["old"]["special_numbers"] == [8]
        assert audit.resolution["new"]["special_numbers"] == [1]
        from lottolab.db import DatasetVersion

        assert db.get(DatasetVersion, frozen_id).draws[0]["special_numbers"] == [8]


def test_financial_changes_not_silently_ignored(session_factory, raw_draw, tmp_path):
    with session_factory() as db:
        add(db, [raw_draw], tmp_path)
        result = add(db, [{**raw_draw, "prizes": {"6": "5"}}], tmp_path)
        assert result["conflicts"] == 1
        assert db.scalar(select(Draw)).prizes == {}
    client, _ = client_for(session_factory, tmp_path)
    issue = client.get("/api/v1/quality").json()["items"][0]
    assert (
        client.post(f"/api/v1/quality/{issue['id']}/resolve", json={"action": "keep_existing"}).status_code
        == 200
    )
    assert client.get("/api/v1/overview").json()["quality_issues"] == 0


def test_revision_audit_matches_persisted_finances_and_source(session_factory, raw_draw, tmp_path):
    with session_factory() as db:
        add(db, [{**raw_draw, "sales": "120.00", "prizes": {"6": "5.00"}}], tmp_path)
        before = freeze_dataset(db, "ssq", "real")
        db.commit()
        incoming = add(db, [{**raw_draw, "special_numbers": [1]}], tmp_path)
        assert incoming["conflicts"] == 1
    client, _ = client_for(session_factory, tmp_path)
    issue = client.get("/api/v1/quality").json()["items"][0]
    response = client.post(
        f"/api/v1/quality/{issue['id']}/resolve",
        json={
            "action": "accept_incoming",
            "expected_identity_hash": issue["existing_identity_hash"],
            "expected_record_hash": issue["existing_record_hash"],
        },
    )
    assert response.status_code == 200
    with session_factory() as db:
        persisted = db.scalar(select(Draw)).public()
        audit = db.get(QualityIssue, issue["id"]).resolution
        assert audit["new"] == persisted
        assert persisted["sales"] == "120.00" and persisted["prizes"] == {"6": "5.00"}
        assert persisted["ingestion_id"] == incoming["id"]
        assert before.draws[0]["ingestion_id"] == audit["old"]["ingestion_id"]
        assert before.draws[0]["special_numbers"] == [8]


def test_write_body_limit_and_invalid_token_encoding(session_factory, tmp_path):
    client, _ = client_for(session_factory, tmp_path)
    assert client.post("/api/v1/simulations", content="x" * 70000).status_code == 413
    remote, _ = client_for(session_factory, tmp_path, local=False, host="203.0.113.8")
    assert remote.get("/api/v1/health", headers={"X-Admin-Token": b"\xff"}).json()["can_write"] is False
