"""刷新各彩种真实一等奖/直选注数 → draws.prizes['winner_count_1']，供撞号实测热度模型使用。

数据源与口径（拿不到的彩种自动跳过、保持结构先验，绝不编造）：
- 福彩 cwl：ssq/qlc 取一等奖(type=1)注数；kl8 取“选十中十”(x10z10)注数；fc3d(3d) 官方不报注数→跳过。
- 体彩 sporttery：dlt(85)/pl3(35)/pl5/qxc 取奖级列表首档(一等奖/直选)注数；gameNo 不对或空→跳过。
用法：DATABASE_URL=<neon> python collector/refresh_winners.py [ssq dlt ...]
"""

import json
import os
import subprocess
import sys
from typing import Any

from contract import normalize_issue
from lottolab.db import Draw, make_engine, make_session_factory
from sqlalchemy import select

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
CWL = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice?name={name}&issueCount=3000"
SPORTTERY = (
    "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
    "?gameNo={gn}&provinceId=0&pageSize=100&isVerify=1&pageNo={page}"
)
# 彩种 → (源, 标识)；标识为 cwl name 或 sporttery gameNo
SOURCES: dict[str, tuple[str, str]] = {
    "ssq": ("cwl", "ssq"),
    "qlc": ("cwl", "qlc"),
    "kl8": ("cwl", "kl8"),
    "fc3d": ("cwl", "3d"),
    "dlt": ("sporttery", "85"),
    "pl3": ("sporttery", "35"),
    "pl5": ("sporttery", "35011"),
    "qxc": ("sporttery", "226"),
}


def _curl(url: str, referer: str) -> str:
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
            f"Referer: {referer}",
            "-s",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=75,
    )
    return r.stdout


def _cwl_winners(name: str) -> dict[str, str]:
    data = json.loads(_curl(CWL.format(name=name), "https://www.cwl.gov.cn/"))
    out: dict[str, str] = {}
    key = "x10z10" if name == "kl8" else 1
    for it in data.get("result", []):
        wn = next((p.get("typenum") for p in it.get("prizegrades", []) if p.get("type") == key), None)
        if wn not in (None, ""):
            out[str(it["code"])] = str(int(str(wn).replace(",", "")))
    return out


def _sporttery_winners(game_no: str, kind: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for page in range(1, 60):
        data = json.loads(_curl(SPORTTERY.format(gn=game_no, page=page), "https://static.sporttery.cn/"))
        lst = (data.get("value") or {}).get("list") or []
        if not lst:
            break
        for it in lst:
            tiers = it.get("prizeLevelList") or []
            cnt = tiers[0].get("stakeCount") if tiers else None
            if cnt in (None, ""):
                continue
            out[normalize_issue(kind, str(it["lotteryDrawNum"]))] = str(int(str(cnt).replace(",", "")))
        if len(lst) < 100:
            break
    return out


def fetch_winners(kind: str) -> dict[str, Any]:
    src, ident = SOURCES[kind]
    try:
        return _cwl_winners(ident) if src == "cwl" else _sporttery_winners(ident, kind)
    except Exception as exc:  # noqa: BLE001 源不可达/解析失败→该彩种保持结构先验
        print(f"[{kind}] 源不可达，跳过：{type(exc).__name__}", flush=True)
        return {}


def main() -> None:
    raw = os.environ.get("DATABASE_URL") or os.environ.get("LOTTOLAB_DATABASE_URL")
    if not raw:
        raise SystemExit("需要 DATABASE_URL")
    url = raw.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    factory = make_session_factory(make_engine(url, pooled=False))
    kinds = sys.argv[1:] or list(SOURCES)
    totals: dict[str, int] = {}
    for kind in kinds:
        winners = fetch_winners(kind)
        updated = 0
        with factory() as s:
            for d in s.scalars(select(Draw).where(Draw.lottery == kind, Draw.dataset_kind == "real")).all():
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
        totals[kind] = updated
        print(f"[{kind}] 源注数 {len(winners)} · 回填更新 {updated}", flush=True)
    print("完成：", totals, flush=True)


if __name__ == "__main__":
    main()
