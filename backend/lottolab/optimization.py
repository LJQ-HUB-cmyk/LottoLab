"""Conditional tuple coverage, explicitly separated from draw prediction."""

from itertools import combinations
from math import comb

import numpy as np

from .analysis import incidence, wilson
from .domain import DISCLAIMER, Rule


def generate_tickets(
    rule: Rule, count: int, seed: int, strategy: str = "uniform", history: list[dict] | None = None
) -> dict:
    rng = np.random.default_rng(seed)
    weights = None
    if strategy != "uniform":
        if not history:
            raise ValueError("频率或冷号策略需要先导入历史数据")
        counts = incidence(history[-100:], rule.main_max, "main_numbers").sum(axis=0) + 1
        weights = counts if strategy == "frequency" else 1 / counts
        weights = weights / weights.sum()
    tickets = []
    seen = set()
    for _ in range(count * 100):
        main = tuple(
            sorted(
                int(v)
                for v in rng.choice(
                    np.arange(1, rule.main_max + 1), rule.main_count, replace=False, p=weights
                )
            )
        )
        special = tuple(
            sorted(
                int(v)
                for v in rng.choice(np.arange(1, rule.special_max + 1), rule.special_count, replace=False)
            )
        )
        key = main, special
        if key not in seen:
            seen.add(key)
            tickets.append({"main_numbers": list(main), "special_numbers": list(special)})
        if len(tickets) == count:
            break
    if len(tickets) != count:
        raise ValueError("无法在资源限制内生成足够的不重复组合")
    return {
        "tickets": tickets,
        "seed": seed,
        "strategy": strategy,
        "theoretical_single_ticket_probability": 1 / rule.combinations,
        "disclaimer": DISCLAIMER,
        "note": "采样权重描述生成方法，不代表实际开奖概率发生改变。",
    }


def optimize_cover(
    rule: Rule,
    candidate_numbers: list[int],
    ticket_count: int,
    target_hits: int,
    seed: int,
    samples: int,
    progress=lambda _value: None,
) -> dict:
    candidates = list(combinations(candidate_numbers, rule.main_count))
    if ticket_count > len(candidates):
        raise ValueError("注数不能超过候选池中不同主区组合的数量")
    tuples = list(combinations(candidate_numbers, target_hits))
    positions = {value: index for index, value in enumerate(tuples)}
    rng = np.random.default_rng(seed)
    rng.shuffle(candidates)
    masks = []
    for candidate in candidates:
        mask = 0
        for subset in combinations(candidate, target_hits):
            mask |= 1 << positions[subset]
        masks.append(mask)
    covered = 0
    chosen = []
    selected = set()
    gains = []
    for step in range(ticket_count):
        best = max(
            (index for index in range(len(candidates)) if index not in selected),
            key=lambda index: (masks[index] & ~covered).bit_count(),
        )
        gain = (masks[best] & ~covered).bit_count()
        selected.add(best)
        chosen.append(candidates[best])
        covered |= masks[best]
        gains.append({"tickets": step + 1, "covered_tuples": covered.bit_count(), "new_tuples": gain})
        progress(int(60 * (step + 1) / ticket_count))
    chosen_masks = [sum(1 << (value - 1) for value in ticket) for ticket in chosen]
    conditional_hits = 0
    for candidate in combinations(candidate_numbers, rule.main_count):
        mask = sum(1 << (value - 1) for value in candidate)
        if any((mask & ticket).bit_count() >= target_hits for ticket in chosen_masks):
            conditional_hits += 1
    successes = 0
    for begin in range(0, samples, 2000):
        size = min(2000, samples - begin)
        draws = (
            np.argpartition(rng.random((size, rule.main_max)), rule.main_count - 1, axis=1)[
                :, : rule.main_count
            ]
            + 1
        )
        hit = np.zeros(size, dtype=bool)
        for ticket in chosen:
            hit |= np.isin(draws, ticket).sum(axis=1) >= target_hits
        successes += int(hit.sum())
    tickets = [
        {
            "main_numbers": list(ticket),
            "special_numbers": sorted(
                int(v)
                for v in rng.choice(np.arange(1, rule.special_max + 1), rule.special_count, replace=False)
            ),
        }
        for ticket in chosen
    ]
    count = covered.bit_count()
    return {
        "lottery": rule.code,
        "candidate_numbers": candidate_numbers,
        "ticket_count": ticket_count,
        "target_hits": target_hits,
        "tickets": tickets,
        "seed": seed,
        "cost": f"{2 * ticket_count:.2f}",
        "tuple_coverage": count / len(tuples),
        "covered_tuples": count,
        "total_tuples": len(tuples),
        "duplicate_tuple_fraction": 1 - count / (ticket_count * comb(rule.main_count, target_hits)),
        "conditional_main_coverage": conditional_hits / len(candidates),
        "conditional_draws_covered": conditional_hits,
        "conditional_draws_total": len(candidates),
        "unconditional_main_coverage": successes / samples,
        "unconditional_confidence_interval": wilson(successes, samples),
        "samples": samples,
        "gains": gains,
        "method": "贪心最大新增子集覆盖；条件主区覆盖精确枚举，完整主区空间覆盖 Monte Carlo 估计",
        "condition": "条件覆盖假设所有主区开奖号码均落在所选候选池内；覆盖目标不包含附加区，不代表中奖奖级。",
        "limitations": "不保证全局最优。候选池外的开奖可能未覆盖；组合优化不提供预测能力。",
        "disclaimer": DISCLAIMER,
    }
