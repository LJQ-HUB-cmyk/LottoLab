"""离线冷门度拟合：库内一等奖注数/销量 + 外配安慰剂注数 → fit_coldness 报告。

安慰剂须是与待验特征无关奖级的真实注数（如双色球二等奖注数），库内没有该列，
必须另备 CSV，不以金额或销量代替。闸门拒绝时 exit 1（适合人工判读与 CI 门禁）。

用法：
    DATABASE_URL=<neon> python scripts/fit_coldness.py --kind dlt --placebo-csv n2.csv
    n2.csv 列：issue,n2（可用 --placebo-col 改列名）
"""

import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from lottolab.coldness import build_fit_rows, fit_coldness  # noqa: E402
from lottolab.db import make_engine, make_session_factory  # noqa: E402
from lottolab.ingestion import load_draws  # noqa: E402


def _arg(name: str, default: str) -> str:
    for i, arg in enumerate(sys.argv):
        if arg.startswith(name):
            return arg.split("=", 1)[1] if "=" in arg else sys.argv[i + 1]
    return default


def _placebo_map(path: str, col: str) -> dict[str, int]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "issue" not in reader.fieldnames or col not in reader.fieldnames:
            raise ValueError(f"{path} 需要 issue、{col} 两列")
        out = {}
        for row in reader:
            out[row["issue"].strip()] = int(row[col])
    if not out:
        raise ValueError(f"{path} 没有数据行")
    return out


def main() -> None:
    kind = _arg("--kind", "dlt")
    col = _arg("--placebo-col", "n2")
    raw_url = os.environ.get("DATABASE_URL") or os.environ.get("LOTTOLAB_DATABASE_URL")
    if not raw_url:
        raise SystemExit("需要 DATABASE_URL（Neon 连接串）或 LOTTOLAB_DATABASE_URL")
    url = raw_url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    placebo = _placebo_map(_arg("--placebo-csv", ""), col)
    factory = make_session_factory(make_engine(url, pooled=False))
    with factory() as session:
        draws = load_draws(session, kind, "real")  # type: ignore[arg-type]
    report = fit_coldness(kind, build_fit_rows(draws, placebo, col), col)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report.get("ok"):
        raise SystemExit(f"拟合被闸门拒绝：{report.get('reason')}")


if __name__ == "__main__":
    main()
