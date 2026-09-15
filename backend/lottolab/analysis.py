"""Descriptive statistics and null models that preserve sampling without replacement."""

from collections import Counter
from functools import lru_cache
from itertools import combinations
from math import comb, sqrt

import numpy as np
from scipy.stats import binomtest, chi2, norm

from .domain import Rule


def incidence(draws: list[dict], maximum: int, field: str, *, digit: bool = False) -> np.ndarray:
    width = maximum + 1 if digit else maximum
    matrix = np.zeros((len(draws), width), dtype=np.float64)
    for index, draw in enumerate(draws):
        values = np.asarray(draw[field], dtype=int)
        columns = values if digit else values - 1
        matrix[index, columns] = 1
    return matrix


def _digit_ranges(rule: Rule) -> list[tuple[int, int]]:
    """DIGIT 各位取值区间：默认 0..main_max，末位若有 last_max 则用 0..last_max。"""
    ranges = [(0, rule.main_max)] * rule.main_count
    if rule.last_max is not None:
        ranges[-1] = (0, rule.last_max)
    return ranges


def _digit_expected_appearance(digit: int, ranges: list[tuple[int, int]]) -> float:
    """均匀零模型下，某数字在一期各位中至少出现一次的概率。"""
    absent = 1.0
    for lo, hi in ranges:
        p = 1.0 / (hi - lo + 1) if lo <= digit <= hi else 0.0
        absent *= 1.0 - p
    return 1.0 - absent


def wilson(successes: int, trials: int) -> list[float]:
    if not trials:
        return [0.0, 1.0]
    z = 1.959963984540054
    proportion = successes / trials
    denominator = 1 + z * z / trials
    center = (proportion + z * z / (2 * trials)) / denominator
    half = z * sqrt(proportion * (1 - proportion) / trials + z * z / (4 * trials * trials)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def overlap_pmf(population: int, chosen: int, drawn: int) -> list[float]:
    denominator = comb(population, drawn)
    return [
        (comb(chosen, k) * comb(population - chosen, drawn - k) / denominator)
        if 0 <= drawn - k <= population - chosen
        else 0.0
        for k in range(min(chosen, drawn) + 1)
    ]


@lru_cache(maxsize=12)
def sum_pmf(population: int, chosen: int) -> tuple[float, ...]:
    maximum = sum(range(population - chosen + 1, population + 1))
    counts = [[0] * (maximum + 1) for _ in range(chosen + 1)]
    counts[0][0] = 1
    for number in range(1, population + 1):
        for count in range(min(number, chosen), 0, -1):
            for total in range(maximum, number - 1, -1):
                counts[count][total] += counts[count - 1][total - number]
    denominator = comb(population, chosen)
    return tuple(count / denominator for count in counts[chosen])


def summarize(draws: list[dict], rule: Rule) -> dict:
    size = len(draws)
    family = rule.family

    trajectory = []
    previous: set[int] = set()
    for draw in draws:
        values = draw["main_numbers"]
        current = set(values)
        trajectory.append(
            {
                "issue": draw["issue"],
                "date": draw["draw_date"],
                "sum": sum(values),
                "span": max(values) - min(values) if values else 0,
                "odd": sum(v % 2 for v in values),
                "consecutive_pairs": sum(b == a + 1 for a, b in zip(values, values[1:], strict=False)),
                "repeated": len(current & previous) if previous else None,
                "high": sum(v > rule.main_max // 2 for v in values),
            }
        )
        previous = current

    structure = {}
    for field in ("span", "odd", "high", "consecutive_pairs", "repeated"):
        values = [row[field] for row in trajectory if row[field] is not None]
        structure[f"mean_{field}"] = sum(values) / len(values) if values else None
    structure["repeat_comparisons"] = max(0, size - 1)
    structure["high_from"] = rule.main_max // 2 + 1
    mean_sum = sum(t["sum"] for t in trajectory) / size if size else None

    if family == "DIGIT":
        ranges = _digit_ranges(rule)
        max_digit = max(hi for _, hi in ranges)
        matrix = incidence(draws, max_digit, "main_numbers", digit=True)
        main_records = []
        for digit in range(max_digit + 1):
            successes = int(matrix[:, digit].sum())
            appearances = np.flatnonzero(matrix[:, digit])
            omission = size - 1 - int(appearances[-1]) if len(appearances) else size
            main_records.append(
                {
                    "number": digit,
                    "count": successes,
                    "frequency": successes / size if size else 0.0,
                    "expected_frequency": _digit_expected_appearance(digit, ranges),
                    "confidence_interval": wilson(successes, size),
                    "omission": omission,
                }
            )
        expected_sum = sum((lo + hi) / 2 for lo, hi in ranges)
        return {
            "family": "digit",
            "sample_size": size,
            "frequency": {"main": main_records, "special": []},
            "trajectory": trajectory[-240:],
            "mean_sum": mean_sum,
            "expected_sum": expected_sum,
            "sum_distribution": [],
            "odd_distribution": [],
            "overlap_pmf": [],
            "regions": [],
            "cooccurrence": [],
            "structure": structure,
            "null_model": "各位数字在自身取值区间内独立均匀（末位含七星彩 0–14）",
        }

    frequencies = {}
    for area, maximum, chosen, field in (
        ("main", rule.main_max, rule.main_count, "main_numbers"),
        ("special", rule.special_max, rule.special_count, "special_numbers"),
    ):
        matrix = incidence(draws, maximum, field)
        records = []
        for index in range(maximum):
            successes = int(matrix[:, index].sum())
            appearances = np.flatnonzero(matrix[:, index])
            omission = size - 1 - int(appearances[-1]) if len(appearances) else size
            records.append(
                {
                    "number": index + 1,
                    "count": successes,
                    "frequency": successes / size if size else 0.0,
                    "expected_frequency": chosen / maximum,
                    "confidence_interval": wilson(successes, size),
                    "omission": omission,
                }
            )
        frequencies[area] = records
    observed_sums = Counter(t["sum"] for t in trajectory)
    theory = sum_pmf(rule.main_max, rule.main_count)
    odds = Counter(t["odd"] for t in trajectory)
    odd_theory = overlap_pmf(rule.main_max, (rule.main_max + 1) // 2, rule.main_count)
    bounds = [0, (rule.main_max + 2) // 3, (2 * rule.main_max + 2) // 3, rule.main_max]
    regions = []
    for low, high in zip(bounds, bounds[1:], strict=False):
        count = sum(low < value <= high for draw in draws for value in draw["main_numbers"])
        regions.append(
            {
                "label": f"{low + 1:02d}–{high:02d}",
                "count": count,
                "mean_per_draw": count / size if size else None,
                "expected_per_draw": rule.main_count * (high - low) / rule.main_max,
            }
        )
    pair_counts = Counter(pair for draw in draws for pair in combinations(draw["main_numbers"], 2))
    pair_probability = rule.main_count * (rule.main_count - 1) / (rule.main_max * (rule.main_max - 1))
    cooccurrence = [
        {
            "numbers": list(pair),
            "count": pair_counts[pair],
            "frequency": pair_counts[pair] / size if size else 0.0,
            "expected_count": size * pair_probability,
        }
        for pair in combinations(range(1, rule.main_max + 1), 2)
    ]
    return {
        "family": "pool",
        "sample_size": size,
        "frequency": frequencies,
        "trajectory": trajectory[-240:],
        "mean_sum": mean_sum,
        "expected_sum": rule.main_count * (rule.main_max + 1) / 2,
        "sum_distribution": [
            {
                "sum": value,
                "observed": observed_sums.get(value, 0),
                "expected": probability * size,
                "probability": probability,
            }
            for value, probability in enumerate(theory)
            if probability
        ],
        "odd_distribution": [
            {"odd": k, "observed": odds.get(k, 0), "expected": odd_theory[k] * size}
            for k in range(rule.main_count + 1)
        ],
        "overlap_pmf": overlap_pmf(rule.main_max, rule.main_count, rule.main_count),
        "regions": regions,
        "cooccurrence": cooccurrence,
        "structure": structure,
        "null_model": "每期完整合法组合独立、均匀；每期内部不放回抽样",
    }


def adjust_pvalues(values: list[float], method: str = "bonferroni") -> list[float]:
    p = np.asarray(values, dtype=float)
    if not len(p):
        return []
    if method == "bonferroni":
        return np.minimum(1, p * len(p)).tolist()
    if method != "bh":
        raise ValueError("未知多重比较方法")
    order = np.argsort(p)
    ranked = p[order] * len(p) / np.arange(1, len(p) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adjusted = np.empty_like(p)
    adjusted[order] = np.minimum(1, ranked)
    return adjusted.tolist()


def _joint_null_statistics(rng, population, chosen, size, trials, include_sum=False):
    expected = size * chosen / population
    frequency_scores = []
    sum_scores = []
    theory = np.asarray(sum_pmf(population, chosen)) if include_sum else None
    cdf = np.cumsum(theory) if theory is not None else None
    for start in range(0, trials, 24):
        batch = min(24, trials - start)
        indices = np.argpartition(rng.random((batch, size, population)), chosen - 1, axis=2)[:, :, :chosen]
        for sample in indices:
            counts = np.bincount(sample.ravel(), minlength=population)
            frequency_scores.append(float(np.sum((counts - expected) ** 2 / expected)))
            if cdf is not None:
                sums = np.sum(sample + 1, axis=1)
                empirical = np.cumsum(np.bincount(sums, minlength=len(cdf))) / size
                sum_scores.append(float(np.max(np.abs(empirical - cdf))))
    return np.asarray(frequency_scores), np.asarray(sum_scores)


def randomness(draws: list[dict], rule: Rule, *, trials: int = 4999, seed: int = 2026) -> dict:
    if rule.family == "DIGIT":
        raise ValueError("随机性检验基于池型不放回零模型，仅对双色球/大乐透等池型彩种提供；数字型彩种不适用")
    size = len(draws)
    if size < 30:
        raise ValueError("随机性检验至少需要 30 期记录")
    if size > 1000 or not 999 <= trials <= 9999:
        raise ValueError("检验限制为最多 1000 期、999–9999 次零模型模拟")
    tests: list[dict] = []
    rng = np.random.default_rng(seed)
    for area, label, maximum, chosen, field in (
        ("main", "主区", rule.main_max, rule.main_count, "main_numbers"),
        ("special", "附加区", rule.special_max, rule.special_count, "special_numbers"),
    ):
        if chosen == 0 or maximum == 0:  # 无该区域号码（如快乐8 无附加区）→ 跳过，避免除零
            continue
        matrix = incidence(draws, maximum, field)
        counts = matrix.sum(axis=0)
        probability = chosen / maximum
        expected = size * probability
        statistic = float(np.sum((counts - expected) ** 2 / expected))
        null_scores, null_sums = _joint_null_statistics(rng, maximum, chosen, size, trials, area == "main")
        tests.append(
            {
                "name": f"{label}整体频率",
                "method": "完整无放回零模型 Monte Carlo",
                "statistic": statistic,
                "p_value": (1 + int(np.sum(null_scores >= statistic))) / (trials + 1),
                "effect_size": float(np.sqrt(np.mean((counts / size - probability) ** 2))),
                "effect_label": "入选频率的均方根偏离",
            }
        )
        if area == "main":
            cdf = np.cumsum(sum_pmf(maximum, chosen))
            sums = [sum(draw[field]) for draw in draws]
            empirical = np.cumsum(np.bincount(sums, minlength=len(cdf))) / size
            distance = float(np.max(np.abs(empirical - cdf)))
            tests.append(
                {
                    "name": "主区和值分布",
                    "method": "离散精确分布 + Monte Carlo 校准",
                    "statistic": distance,
                    "p_value": (1 + int(np.sum(null_sums >= distance))) / (trials + 1),
                    "effect_size": distance,
                    "effect_label": "经验与理论 CDF 的最大距离",
                }
            )
        for index in range(maximum):
            successes = int(counts[index])
            tests.append(
                {
                    "name": f"{label} {index + 1:02d} 入选频率",
                    "method": "单号码精确二项检验（按期）",
                    "statistic": successes,
                    "p_value": float(binomtest(successes, size, probability).pvalue),
                    "effect_size": successes / size - probability,
                    "effect_label": "入选频率差",
                    "confidence_interval": wilson(successes, size),
                }
            )
            x = matrix[:, index]
            n1, n0 = successes, size - successes
            if n1 >= 5 and n0 >= 5:
                runs = 1 + int(np.count_nonzero(np.diff(x)))
                expected_runs = 1 + 2 * n1 * n0 / size
                variance = 2 * n1 * n0 * (2 * n1 * n0 - size) / (size * size * (size - 1))
                z = max(0, abs(runs - expected_runs) - 0.5) / sqrt(variance)
                tests.append(
                    {
                        "name": f"{label} {index + 1:02d} 游程",
                        "method": "二元序列游程（正态近似、连续性校正）",
                        "statistic": runs,
                        "p_value": float(2 * norm.sf(z)),
                        "effect_size": runs - expected_runs,
                        "effect_label": "游程数差",
                    }
                )
            centered = x - x.mean()
            denominator = float(np.dot(centered, centered))
            if denominator > 0:
                lags = min(10, size // 5)
                acf = np.asarray(
                    [np.dot(centered[k:], centered[:-k]) / denominator for k in range(1, lags + 1)]
                )
                q = float(size * (size + 2) * np.sum(acf**2 / (size - np.arange(1, lags + 1))))
                tests.append(
                    {
                        "name": f"{label} {index + 1:02d} 序列相关",
                        "method": f"Ljung–Box（{lags} 阶、渐近近似）",
                        "statistic": q,
                        "p_value": float(chi2.sf(q, lags)),
                        "effect_size": float(np.max(np.abs(acf))),
                        "effect_label": "最大绝对自相关",
                    }
                )
    # Keep the family size fixed even when constant/sparse sequences cannot be tested.
    planned_family_size = 3 + 3 * (rule.main_max + rule.special_max)
    adjusted = [min(1.0, test["p_value"] * planned_family_size) for test in tests]
    for test, value in zip(tests, adjusted, strict=True):
        test["adjusted_p_value"] = value
        test["significant"] = value < 0.05
    significant = sum(test["significant"] for test in tests)
    return {
        "sample_size": size,
        "trials": trials,
        "seed": seed,
        "correction": "bonferroni",
        "number_of_tests": len(tests),
        "correction_family_size": planned_family_size,
        "significant_count": significant,
        "verdict": "REVIEW_NEEDED" if significant else "NOT_SIGNIFICANT",
        "tests": tests,
        "start_issue": draws[0]["issue"],
        "end_issue": draws[-1]["issue"],
        "interpretation": "校正后存在需要复核的偏离；不等于可预测。"
        if significant
        else "本次检验未检出校正后显著偏离；这不证明绝对随机。",
        "limitations": [
            "一次开奖为抽样单元；同期开奖内依赖通过完整无放回零模型处理。",
            "游程与 Ljung–Box 的 p 值是近似值；有限样本检验功效有限。",
            f"Monte Carlo p 值分辨率为 1/{trials + 1}；预设检验族 {planned_family_size} 项，实际可计算 {len(tests)} 项，按预设族做 Bonferroni 校正。",
        ],
    }


def simulate(rule: Rule, iterations: int, seed: int) -> dict:
    if not 1000 <= iterations <= 1000000:
        raise ValueError("模拟次数必须在 1000–1000000 之间")
    rng = np.random.default_rng(seed)
    main = rng.hypergeometric(
        rule.main_count, rule.main_max - rule.main_count, rule.main_count, size=iterations
    )
    special = rng.hypergeometric(
        rule.special_count, rule.special_max - rule.special_count, rule.special_count, size=iterations
    )
    histogram = np.bincount(main, minlength=rule.main_count + 1)
    exact = overlap_pmf(rule.main_max, rule.main_count, rule.main_count)
    jackpots = int(np.sum((main == rule.main_count) & (special == rule.special_count)))
    mean = float(main.mean())
    standard_error = float(main.std(ddof=1) / sqrt(iterations))
    return {
        "iterations": iterations,
        "seed": seed,
        "lottery": rule.code,
        "distribution": [
            {
                "hits": k,
                "count": int(histogram[k]),
                "observed": float(histogram[k] / iterations),
                "theoretical": exact[k],
                "confidence_interval": wilson(int(histogram[k]), iterations),
            }
            for k in range(rule.main_count + 1)
        ],
        "mean_hits": mean,
        "expected_hits": rule.main_count**2 / rule.main_max,
        "mean_confidence_interval": [mean - 1.96 * standard_error, mean + 1.96 * standard_error],
        "jackpots": jackpots,
        "jackpot_probability": 1 / rule.combinations,
        "jackpot_confidence_interval": wilson(jackpots, iterations),
        "method": "固定一注与均匀合法开奖的交集，按精确超几何分布采样",
        "note": "极小概率使用组合公式；有限次数中未出现头奖，不代表头奖概率为零。",
    }
