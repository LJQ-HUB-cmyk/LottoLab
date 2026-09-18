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


def _ols_coefs(design: np.ndarray, target: np.ndarray) -> np.ndarray:
    """最小二乘系数；design 首列为截距。"""
    coefs, *_ = np.linalg.lstsq(design, target, rcond=None)
    return np.asarray(coefs, dtype=float)


def fit_coldness(
    kind: str,
    rows: list[dict[str, Any]],
    placebo_col: str = "n2",
    train_ratio: float = 0.7,
    placebo_tol: float = 0.05,
) -> dict[str, Any]:
    """从真实一等奖注数拟合各特征乘子，带样本外验证与安慰剂闸门。

    模型：log1p(n1) = a + b·log(sales) + Σ cⱼ·featⱼ，销量做协变量进入回归。
    按列表顺序（应为时间升序）前 train_ratio 拟合、后段验证：保留特征需乘子
    在 1 的同侧（符号一致），反号即该特征样本外不成立。
    安慰剂：同一设计矩阵打在 placebo_col 奖级注数上，任一保留特征
    |log 乘子| > placebo_tol 即判混淆，整轮拒绝（ok=False，fail-closed）。
    rows 每行需含 main_numbers / special_numbers / winner_count_1 / sales，
    安慰剂列缺失同样拒绝，避免无对照放行。
    """

    feats = [f[0] for f in _feature_template(kind)]
    vecs: list[list[int]] = []
    goals: list[float] = []
    placebos: list[float] = []
    log_sales: list[float] = []
    for r in rows:
        try:
            n1 = r.get("winner_count_1")
            sales = float(r.get("sales") or 0)
            if n1 is None or sales <= 0:
                continue
            n1v = r.get(placebo_col)
            if n1v is None:
                return {"ok": False, "reason": f"缺少安慰剂对照列 {placebo_col}，拒绝无对照发布"}
            main = [int(x) for x in r["main_numbers"]]
            aux = [int(v) for v in (r.get("special_numbers") or [])]
            f = _features(kind, main, aux)
            vecs.append([f.get(k, 0) for k in feats])
            goals.append(math.log1p(int(n1)))
            placebos.append(math.log1p(int(n1v)))
            log_sales.append(math.log(sales))
        except (TypeError, ValueError, KeyError):
            continue
    if len(vecs) < 200:
        return {"ok": False, "reason": "样本不足"}
    full = np.asarray(vecs, dtype=float)
    keep = [j for j in range(full.shape[1]) if full[:, j].sum() >= 30]
    if not keep:
        return {"ok": False, "reason": "无足够覆盖的特征"}
    kept = [feats[j] for j in keep]

    def design(part: np.ndarray, sales: np.ndarray) -> np.ndarray:
        ones = np.ones((part.shape[0], 1))
        return np.hstack([ones, sales.reshape(-1, 1), part[:, keep]])

    X = full
    S = np.asarray(log_sales, dtype=float)
    Y = np.asarray(goals, dtype=float)
    P = np.asarray(placebos, dtype=float)
    cut = int(len(vecs) * train_ratio)
    if len(vecs) - cut < 30:
        return {"ok": False, "reason": "验证段不足 30 期"}
    train_coef = _ols_coefs(design(X[:cut], S[:cut]), Y[:cut])[2:]
    test_coef = _ols_coefs(design(X[cut:], S[cut:]), Y[cut:])[2:]
    train_mult = [round(float(math.exp(c)), 3) for c in train_coef]
    test_mult = [round(float(math.exp(c)), 3) for c in test_coef]

    validated: dict[str, float] = {}
    dropped: dict[str, str] = {}
    for name, tr, te in zip(kept, train_mult, test_mult, strict=True):
        if (tr - 1) * (te - 1) > 0:
            validated[name] = tr
        else:
            dropped[name] = f"样本外反号（训练 {tr} / 验证 {te}），不发布"

    full_coef = _ols_coefs(design(X, S), P)[2:]
    worst = max((abs(float(c)), name) for c, name in zip(full_coef, kept, strict=True))
    placebo_report = {"col": placebo_col, "max_abs_log_mult": round(worst[0], 4), "tol": placebo_tol}
    if worst[0] > placebo_tol:
        return {
            "ok": False,
            "reason": f"安慰剂 {placebo_col} 上 {worst[1]} 偏离 1（|log|={worst[0]:.3f}），判混淆",
            "kind": kind,
            "n": len(vecs),
            "validated": validated,
            "dropped": dropped,
            "placebo": {**placebo_report, "pass": False},
        }
    if not validated:
        return {
            "ok": False,
            "reason": "无通过样本外验证的特征",
            "kind": kind,
            "n": len(vecs),
            "dropped": dropped,
            "placebo": {**placebo_report, "pass": True},
        }
    return {
        "ok": True,
        "kind": kind,
        "multipliers": validated,
        "dropped": dropped,
        "n": len(vecs),
        "n_train": cut,
        "n_test": len(vecs) - cut,
        "train_multipliers": dict(zip(kept, train_mult, strict=True)),
        "test_multipliers": dict(zip(kept, test_mult, strict=True)),
        "placebo": {**placebo_report, "pass": True},
    }


def _feature_template(kind: str) -> list[tuple[str, str, float]]:
    return FACTORS.get(kind) or [
        (k, k, 1.0) for k in ["allLe31", "hasTail8", "hasTail4", "auxHot", "auxCold"]
    ]
