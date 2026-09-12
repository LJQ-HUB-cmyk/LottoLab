"""Verify the private Compose deployment, including nonempty restart persistence."""

import argparse
import hashlib
import json
import time
from pathlib import Path

import httpx
from lottolab import __version__
from lottolab.config import get_settings

root = Path(__file__).resolve().parents[1]
settings = get_settings()
base = "http://127.0.0.1:18080"
parser = argparse.ArgumentParser(description=__doc__)
mode = parser.add_mutually_exclusive_group()
mode.add_argument("--after-restart", action="store_true", help="Verify saved records, snapshots and results")
mode.add_argument(
    "--seed-fixtures", action="store_true", help="Seed synthetic SSQ/DLT only in an empty test DB"
)
args = parser.parse_args()
report_path = root / ".local" / "container-verification.json"
report_path.parent.mkdir(exist_ok=True)


def wait_job(client, path, payload):
    response = client.post(path, json=payload)
    response.raise_for_status()
    job_id = response.json()["id"]
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/jobs/{job_id}")
        response.raise_for_status()
        job = response.json()
        if job["status"] in {"failed", "cancelled"}:
            raise RuntimeError(f"Container job did not complete: {job['status']}")
        if job["status"] == "completed":
            return job
        time.sleep(0.5)
    raise RuntimeError("Container worker did not finish within 60 seconds")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def data_state(client):
    state = {}
    for lottery in ("ssq", "dlt"):
        for kind in ("real", "synthetic"):
            params = {"lottery": lottery, "dataset_kind": kind}
            response = client.get("/api/v1/draws", params={**params, "limit": 1})
            response.raise_for_status()
            exported = client.get("/api/v1/draws/export", params=params)
            exported.raise_for_status()
            ingestions = client.get("/api/v1/ingestions", params=params)
            ingestions.raise_for_status()
            state[f"{lottery}:{kind}"] = {
                "count": response.json()["total"],
                "csv_sha256": hashlib.sha256(exported.content).hexdigest(),
                "ingestions_sha256": fingerprint(ingestions.json()),
            }
    return state


with httpx.Client(base_url=base, timeout=15, trust_env=False) as client:
    try:
        health = client.get("/api/v1/health")
    except httpx.RequestError as exc:
        raise SystemExit(f"Container API unavailable; start Compose first. ({type(exc).__name__})") from None
    health.raise_for_status()
    assert health.json()["database"] == "postgresql"
    assert health.json()["version"] == __version__
    assert health.json()["can_write"] is False
    assert client.post("/api/v1/simulations", json={"iterations": 1000}).status_code == 403
    page = client.get("/")
    page.raise_for_status()
    assert "LottoLab" in page.text
    client.headers["X-Admin-Token"] = settings.admin_token
    assert client.get("/api/v1/health").json()["can_write"] is True
    state = data_state(client)
    if args.after_restart:
        if not report_path.is_file():
            raise SystemExit("Run the initial smoke check before testing a restart.")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert state == report["data_state"], "Draws or ingestion audit changed across the restart"
        saved = client.get(f"/api/v1/jobs/{report['job_id']}")
        saved.raise_for_status()
        assert saved.json()["status"] == "completed"
        assert fingerprint(saved.json()["result"]) == report["result_sha256"]
        report["restart_persistence"] = "PASS"
    else:
        if args.seed_fixtures:
            histories = [
                client.get("/api/v1/jobs", params={"lottery": lottery}).json() for lottery in ("ssq", "dlt")
            ]
            if any(row["count"] for row in state.values()) or any(item["items"] for item in histories):
                raise SystemExit(
                    "Fixture seeding requires an empty isolated database; existing data preserved."
                )
            for lottery in ("ssq", "dlt"):
                job = wait_job(
                    client, "/api/v1/datasets/demo", {"lottery": lottery, "count": 100, "seed": 9026}
                )
                assert job["result"]["accepted"] == 100
            state = data_state(client)
            assert all(state[f"{lottery}:synthetic"]["count"] == 100 for lottery in ("ssq", "dlt"))
        job = wait_job(client, "/api/v1/simulations", {"lottery": "ssq", "iterations": 1000, "seed": 9026})
        assert job["result"]["iterations"] == 1000
        assert job["result"]["execution"]["packages"]["lottolab"] == __version__
        report = {
            "version": __version__,
            "container_api": "PASS",
            "container_frontend": "PASS",
            "anonymous_writes_denied": "PASS",
            "authenticated_job": "PASS",
            "fixtures": "synthetic" if args.seed_fixtures else "existing_data",
            "job_id": job["id"],
            "result_sha256": fingerprint(job["result"]),
            "data_state": state,
        }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
