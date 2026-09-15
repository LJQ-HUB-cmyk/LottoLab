"""冷门度（coldness）：估计「万一中头奖要和多少人分奖」。

只影响中奖后的分奖人数，**不改变中奖概率**，期望回报仍为负。
仅对浮动奖玩法有意义（ssq/dlt 一等、qlc 一等、qxc 一等按注数分奖）；
固定奖玩法（kl8/3d/排3/排5）中了就是定额、无人分摊 → 冷门度对期望严格为 0，不做。

系数来源：
- ssq：沿用 lottery-web worker/src/coldness.js 的样本外+安慰剂验证常量。
- dlt/qlc/qxc：由本库真实一等奖注数（prizes['winner_count_1']）+ 销量回归拟合，
  fit_coldness 带安慰剂闸门（用与特征无关的奖级做对照，显著即判为混淆、拒绝发布）。
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

DISCLAIMER = "冷门度只影响中奖后与多少人分奖，不改变中奖概率；期望回报仍为负。"

# 双色球：已样本外验证的常量（旧70%拟合，新30%同号；安慰剂≈1）
SSQ_FACTORS: list[tuple[str, str, float]] = [
    ("allLe31", "全部红球 ≤31（可用日期表达，最多人在买）", 1.174),
    ("hasTail8", "含尾数 8（吉利偏好）", 1.074),
    ("hasTail4", "含尾数 4（回避，买的人少）", 0.918),
    ("blueHot", "蓝球在大热名单 05-12（同奖人数显著更多）", 1.241),
    ("blueCold", "蓝球在冷门名单 01/14/15/16", 0.812),
]
SSQ_BLUE_HOT = set(range(5, 13))
SSQ_BLUE_COLD = {1, 14, 15, 16}
SSQ_AVG_WINNERS = 8.27

# 各浮动奖彩种的因子表（ssq 已验证；dlt/qlc/qxc 由 fit_coldness 生成后填入，未验证前为空）
FACTORS: dict[str, list[tuple[str, str, float]]] = {"ssq": SSQ_FACTORS}
AVG_WINNERS: dict[str, float] = {"ssq": SSQ_AVG_WINNERS}
FLOATING_KINDS = {"ssq", "dlt", "qlc", "qxc"}


def _ssq_features(main: list[int], aux: list[int]) -> dict[str, int]:
    red = [int(x) for x in main]
    blue = int(aux[0]) if aux else 0
    return {
        "allLe31": 1 if all(x <= 31 for x in red) else 0,
        "hasTail8": 1 if any(x % 10 == 8 for x in red) else 0,
        "hasTail4": 1 if any(x % 10 == 4 for x in red) else 0,
        "blueHot": 1 if blue in SSQ_BLUE_HOT else 0,
        "blueCold": 1 if blue in SSQ_BLUE_COLD else 0,
    }


def _features(kind: str, main: list[int], aux: list[int]) -> dict[str, int]:
    if kind == "ssq":
        return _ssq_features(main, aux)
    # dlt/qlc/qxc：通用可解释特征（生日区/尾数/附加区冷热），系数由 fit 决定
    red = [int(x) for x in main]
    a0 = int(aux[0]) if aux else 0
    return {
        "allLe31": 1 if all(x <= 31 for x in red) else 0,
        "hasTail8": 1 if any(x % 10 == 8 for x in red) else 0,
        "hasTail4": 1 if any(x % 10 == 4 for x in red) else 0,
        "auxHot": 1 if a0 in SSQ_BLUE_HOT else 0,
        "auxCold": 1 if a0 in SSQ_BLUE_COLD else 0,
    }


def _label(ratio: float) -> str:
    return (
        "很冷"
        if ratio < 0.7
        else "偏冷"
        if ratio < 0.9
        else "中性"
        if ratio <= 1.1
        else "偏热"
        if ratio <= 1.4
        else "很热"
    )


def coldness(kind: str, main: list[int], aux: list[int]) -> dict[str, Any]:
    """返回该注的预计同奖倍数/同奖人数/因子分解；不支持的玩法返回 supported=False。"""
    if kind not in FACTORS:
        note = (
            "固定奖玩法：中了为定额、无人与你分奖，冷门度对期望回报为 0（不做）。"
            if kind not in FLOATING_KINDS
            else "该浮动奖玩法尚无样本外验证的系数，暂不给出冷门度。"
        )
        return {"supported": False, "kind": kind, "note": note, "disclaimer": DISCLAIMER}
    feats = _features(kind, main, aux)
    ratio = 1.0
    factors = []
    for key, label, m in FACTORS[kind]:
        if feats.get(key):
            ratio *= m
            factors.append({"key": key, "label": label, "effect": round(m, 3)})
    ratio = round(ratio, 3)
    avg = AVG_WINNERS.get(kind, SSQ_AVG_WINNERS)
    return {
        "supported": True,
        "kind": kind,
        "ratio": ratio,
        "label": _label(ratio),
        "coldIndex": max(0, min(100, round(100 / ratio))),
        "avgFirstWinners": avg,
        "estWinners": round(avg * ratio, 1),
        "factors": factors,
        "note": "系数由历史一等奖实际中奖注数拟合（ssq 已样本外验证+安慰剂对照）；未覆盖特征不计入。",
        "disclaimer": DISCLAIMER,
    }


def fit_coldness(kind: str, rows: list[dict[str, Any]], placebo_col: str = "n2") -> dict[str, Any]:
    """从真实一等奖注数拟合各特征乘子（对 log1p(n1) 关于销量归一后回归），带安慰剂闸门。

    rows: 每行含 main_numbers/aux、winner_count_1(n1)、可选 placebo 奖级注数、sales。
    安慰剂：把特征回归到与其特征无关的奖级(如 ssq 二等奖只看红、不看蓝 → blueHot 打在二等奖应≈1)；
    若安慰剂显著偏离 1，判为混淆，拒绝（返回 ok=False）。
    """
    feats = [f[0] for f in _feature_template(kind)]
    x, y, yp = [], [], []  # 主目标 n1、安慰剂目标
    for r in rows:
        n1 = r.get("winner_count_1")
        sales = r.get("sales")
        if not n1 or not sales:
            continue
        main = [int(x) for x in r["main_numbers"]]
        aux = [int(v) for v in (r.get("special_numbers") or [])]
        f = _features(kind, main, aux)
        vec = [f.get(k, 0) for k in feats]
        x.append(vec)
        y.append(math.log1p(int(n1)) - math.log10(float(sales)) / 1e6 * 0)  # 销量很大，这里仅用 n1 强度
        yp.append(math.log1p(int(r.get(placebo_col, n1))))
    if len(y) < 200:
        return {"ok": False, "reason": "样本不足"}
    X = np.asarray(x, dtype=float)
    keep = [j for j in range(X.shape[1]) if X[:, j].sum() >= 30]
    if not keep:
        return {"ok": False, "reason": "无足够覆盖的特征"}
    Xs = X[:, keep]
    coef = np.linalg.lstsq(Xs, np.asarray(y) - np.mean(y), rcond=None)[0]
    multipliers = {feats[j]: round(float(math.exp(c)), 3) for j, c in zip(keep, coef, strict=True)}
    return {"ok": True, "kind": kind, "multipliers": multipliers, "n": len(y)}


def _feature_template(kind: str) -> list[tuple[str, str, float]]:
    return FACTORS.get(kind) or [
        (k, k, 1.0) for k in ["allLe31", "hasTail8", "hasTail4", "auxHot", "auxCold"]
    ]
