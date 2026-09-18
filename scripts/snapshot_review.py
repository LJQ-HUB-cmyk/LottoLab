"""每日复盘快照：同步完成后，用当日数据为池型彩种生成推荐并登记到预测台账。

目标期号按当前最大期号序号 +1 推算；猜错（跨年/特殊赛程）时该行永久待对账，
不影响已有记录。同一目标期已登记则跳过，每日重跑幂等。

用法：
    DATABASE_URL=<neon-url> python scripts/snapshot_review.py
    DATABASE_URL=... python scripts/snapshot_review.py --kinds ssq,dlt --seed 20260919
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from lottolab.db import make_engine, make_session_factory  # noqa: E402
from lottolab.ingestion import load_draws  # noqa: E402
from lottolab.predict import online_rows  # noqa: E402
from lottolab.review import snapshot_review  # noqa: E402

KINDS = ("ssq", "dlt")


def _kinds() -> list[str]:
    for i, arg in enumerate(sys.argv):
        if arg.startswith("--kinds"):
            value = arg.split("=", 1)[1] if "=" in arg else sys.argv[i + 1]
            kinds = [k.strip() for k in value.split(",") if k.strip() in KINDS]
            if kinds:
                return kinds
    return list(KINDS)


def _seed() -> int:
    for i, arg in enumerate(sys.argv):
        if arg.startswith("--seed"):
            value = arg.split("=", 1)[1] if "=" in arg else sys.argv[i + 1]
            return int(value)
    return int(datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d"))


def main() -> None:
    raw_url = os.environ.get("DATABASE_URL") or os.environ.get("LOTTOLAB_DATABASE_URL")
    if not raw_url:
        raise SystemExit("需要 DATABASE_URL（Neon 连接串）或 LOTTOLAB_DATABASE_URL")
    url = raw_url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    factory = make_session_factory(make_engine(url, pooled=False))
    seed = _seed()
    for kind in _kinds():
        with factory() as session:
            rows = load_draws(session, kind, "real")  # type: ignore[arg-type]
            result = snapshot_review(session, kind, online_rows(kind, rows), seed)
        print(f"[{kind}] {result}", flush=True)


if __name__ == "__main__":
    main()
