"""Verified copy into an empty database, including immutable source evidence."""

import gzip
import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import Connection, Engine

from .db import Base, RawSnapshot
from .ingestion import canonical
from .snapshots import snapshot_bytes


def _empty_target(connection: Connection) -> None:
    names = set(inspect(connection).get_table_names()) - {"alembic_version"}
    if names - set(Base.metadata.tables):
        raise ValueError("目标数据库含其他应用的表，请使用 LottoLab 专属空数据库")
    for name in names:
        if connection.scalar(select(func.count()).select_from(Base.metadata.tables[name])):
            raise ValueError("目标数据库已有数据；已停止，未覆盖任何记录")


def _fingerprint(rows: list[dict]) -> str:
    normalized = []
    for row in rows:
        values = dict(row)
        for key, value in values.items():
            if isinstance(value, datetime):
                values[key] = value.replace(tzinfo=value.tzinfo or UTC).astimezone(UTC).isoformat()
            elif isinstance(value, bytes):
                values[key] = hashlib.sha256(value).hexdigest()
        normalized.append(values)
    return hashlib.sha256(canonical(sorted(normalized, key=lambda row: row["id"]))).hexdigest()


def _read_source(connection: Connection, raw_dir: Path) -> dict[str, list[dict]]:
    names = set(inspect(connection).get_table_names())
    required = set(Base.metadata.tables) - {"raw_snapshots"}
    if not required.issubset(names):
        raise ValueError("来源数据库缺少 LottoLab 表，请先检查本地迁移版本")
    records = {
        table.name: [dict(row) for row in connection.execute(select(table)).mappings()]
        if table.name in names
        else []
        for table in Base.metadata.sorted_tables
    }
    # SQLite drops timezone metadata; all application timestamps are written in UTC.
    # Restore it before PostgreSQL interprets a naive value in its server timezone.
    for rows in records.values():
        for row in rows:
            for key, value in row.items():
                if isinstance(value, datetime):
                    # Normalize aware PostgreSQL values too, before SQLite drops their offsets.
                    row[key] = value.replace(tzinfo=value.tzinfo or UTC).astimezone(UTC)
    if any(row["status"] in {"queued", "running"} for row in records["jobs"]):
        raise ValueError("来源有排队或运行中的任务，请等待完成或取消后再迁移")
    snapshots = {row["id"]: row for row in records["raw_snapshots"]}
    for row in snapshots.values():
        snapshot_bytes(RawSnapshot(**row))
    raw_dir = raw_dir.resolve()
    for run in sorted(records["ingestion_runs"], key=lambda row: row["created_at"]):
        checksum = run["snapshot_hash"]
        if not re.fullmatch(r"[a-f0-9]{64}", checksum):
            raise ValueError("来源快照 SHA-256 格式不合法")
        if checksum in snapshots:
            continue
        path = (raw_dir / f"{checksum}.snapshot").resolve()
        if not path.is_relative_to(raw_dir) or not path.is_file():
            raise ValueError("来源原始快照缺失或路径无效，已停止迁移")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != checksum:
            raise ValueError("来源原始快照校验失败，已停止迁移")
        snapshots[checksum] = {
            "id": checksum,
            "content": gzip.compress(raw, mtime=0),
            "raw_size": len(raw),
            "created_at": run["created_at"],
        }
    records["raw_snapshots"] = list(snapshots.values())
    return records


def transfer_database(
    source_engine: Engine,
    target_engine: Engine,
    *,
    raw_dir: Path,
    project_dir: Path,
    apply: bool = False,
) -> dict:
    """Validate first; a dry run never changes the destination or the source."""
    with source_engine.begin() as source:
        if source.dialect.name == "sqlite":
            # sqlite3's legacy transaction mode does not begin a read snapshot itself.
            source.exec_driver_sql("BEGIN")
        elif source.dialect.name == "postgresql":
            source.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        records = _read_source(source, raw_dir)
    fingerprints = {name: _fingerprint(rows) for name, rows in records.items()}
    report = {
        "status": "DRY_RUN",
        "rows": {name: len(rows) for name, rows in records.items()},
        "fingerprints": fingerprints,
        "snapshot_raw_bytes": sum(row["raw_size"] for row in records["raw_snapshots"]),
        "snapshot_stored_bytes": sum(len(row["content"]) for row in records["raw_snapshots"]),
    }
    with target_engine.connect() as target:
        _empty_target(target)
    if not apply:
        return report
    with target_engine.begin() as target:
        if target.dialect.name == "sqlite":
            target.exec_driver_sql("BEGIN IMMEDIATE")
        elif target.dialect.name == "postgresql":
            target.execute(text("SELECT pg_advisory_xact_lock(736823615)"))
        _empty_target(target)
        config = Config(str(project_dir / "alembic.ini"))
        config.set_main_option("script_location", str(project_dir / "migrations"))
        config.attributes["connection"] = target
        command.upgrade(config, "head")
        if target.dialect.name == "postgresql":
            # Fixed identifiers from our own metadata, never user-supplied names.
            tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
            target.execute(text(f"LOCK TABLE {tables} IN ACCESS EXCLUSIVE MODE"))
        _empty_target(target)
        for table in Base.metadata.sorted_tables:
            if records[table.name]:
                target.execute(table.insert(), records[table.name])
        for table in Base.metadata.sorted_tables:
            copied = [dict(row) for row in target.execute(select(table)).mappings()]
            if _fingerprint(copied) != fingerprints[table.name]:
                raise ValueError(f"{table.name} 迁移前后不一致，目标事务已回滚")
        report["status"] = "PASS"
    return report
