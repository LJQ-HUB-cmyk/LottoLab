"""刷新双色球真实一等奖注数：cwl → draws.prizes['winner_count_1']，供撞号实测热度模型使用。

用法：
    DATABASE_URL=<neon-url> python collector/refresh_winners.py
说明：
    - 只更新已收录 ssq 期次的 prizes['winner_count_1']，不改号码/期号；
    - cwl 为福彩官方源，境外 CI 可能不可达；本地或可达网络下按需刷新；
    - 撞号模型在样本 <200 期时自动回退到结构先验，故此刷新为“增强”，非必需。
"""

import json
import os
import subprocess

from lottolab.db import Draw, make_engine, make_session_factory
from sqlalchemy import select

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
CWL = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name=ssq&issueCount={n}"


def fetch_cwl(n: int = 1000) -> dict[str, str]:
    r = subprocess.run(  # noqa: S603
        [
            "curl",
            "-k",
            "--ssl-no-revoke",
            "--max-time",
            "60",
            "-A",
            UA,
            "-H",
            "Referer: https://www.cwl.gov.cn/",
            "-s",
            CWL.format(n=n),
        ],
        capture_output=True,
        text=True,
        timeout=75,
    )
    data = json.loads(r.stdout)
    out: dict[str, str] = {}
    for it in data.get("result", []):
        wn = next((p.get("typenum") for p in it.get("prizegrades", []) if p.get("type") == 1), None)
        if wn is not None:
            out[str(it["code"])] = str(wn)
    return out


def main() -> None:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("LOTTOLAB_DATABASE_URL")
    if not raw:
        raise SystemExit("需要 DATABASE_URL")
    url = raw.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    winners = fetch_cwl()
    print("cwl winner-count rows:", len(winners), flush=True)
    factory = make_session_factory(make_engine(url, pooled=False))
    updated = 0
    with factory() as s:
        for d in s.scalars(select(Draw).where(Draw.lottery == "ssq", Draw.dataset_kind == "real")).all():
            w = winners.get(d.issue)
            if w is None:
                continue
            prizes = dict(d.prizes or {})
            if prizes.get("winner_count_1") == w:
                continue
            prizes["winner_count_1"] = w
            d.prizes = prizes
            updated += 1
        s.commit()
    print("updated ssq rows with winner_count_1:", updated, flush=True)


if __name__ == "__main__":
    main()
