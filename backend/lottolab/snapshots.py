"""Content-addressed raw responses, with durable storage for stateless hosts."""

import gzip
import hashlib
import zlib
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import RawSnapshot


def snapshot_bytes(snapshot: RawSnapshot) -> bytes:
    try:
        raw = gzip.decompress(snapshot.content)
    except (OSError, EOFError, zlib.error) as exc:
        raise ValueError("原始快照压缩内容损坏") from exc
    if len(raw) != snapshot.raw_size or hashlib.sha256(raw).hexdigest() != snapshot.id:
        raise ValueError("原始快照校验失败")
    return raw


def save_snapshot(session: Session, raw: bytes, directory: Path | None) -> str:
    checksum = hashlib.sha256(raw).hexdigest()
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{checksum}.snapshot"
        if path.exists():
            if path.read_bytes() != raw:
                raise ValueError("已有原始快照内容与校验值不符，导入已停止")
        else:
            # Exclusive creation preserves an existing snapshot under concurrent imports.
            try:
                with path.open("xb") as stream:
                    stream.write(raw)
            except FileExistsError:
                if path.read_bytes() != raw:
                    raise ValueError("并发写入的原始快照未通过校验") from None
        return checksum
    existing = session.get(RawSnapshot, checksum)
    if existing is None:
        try:
            with session.begin_nested():
                session.add(RawSnapshot(id=checksum, content=gzip.compress(raw, mtime=0), raw_size=len(raw)))
                session.flush()
        except IntegrityError:
            existing = session.get(RawSnapshot, checksum)
            if existing is None:
                raise
    if existing is not None and snapshot_bytes(existing) != raw:
        raise ValueError("数据库中的原始快照未通过校验")
    return checksum
