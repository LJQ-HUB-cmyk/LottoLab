from collections import Counter
from itertools import combinations
from math import comb

import numpy as np
import pytest
from lottolab.analysis import adjust_pvalues, overlap_pmf, randomness, simulate, sum_pmf, summarize, wilson
from lottolab.domain import RULES
from lottolab.ingestion import synthetic_records
from lottolab.optimization import optimize_cover


def test_exact_overlap_distribution_matches_enumeration():
    outcomes = list(combinations(range(1, 9), 3))
    counts = Counter(len(set(outcome) & {1, 2, 3}) for outcome in outcomes)
    np.testing.assert_allclose(overlap_pmf(8, 3, 3), [counts[k] / len(outcomes) for k in range(4)])
    ssq = overlap_pmf(33, 6, 6)
    assert sum(ssq) == pytest.approx(1)
    assert sum(k * p for k, p in enumerate(ssq)) == pytest.approx(36 / 33)
    assert ssq[6] == pytest.approx(1 / comb(33, 6))


def test_sum_distribution_matches_small_exhaustive_space():
    counts = Counter(sum(outcome) for outcome in combinations(range(1, 8), 3))
    pmf = sum_pmf(7, 3)
    np.testing.assert_allclose(pmf, [counts[k] / comb(7, 3) for k in range(len(pmf))])
    assert sum(sum_pmf(33, 6)) == pytest.approx(1)


def test_multiple_testing_and_zero_event_interval():
    assert adjust_pvalues([0.01, 0.03, 0.2]) == pytest.approx([0.03, 0.09, 0.6])
    assert adjust_pvalues([0.01, 0.03, 0.2], "bh") == pytest.approx([0.03, 0.045, 0.2])
    low, high = wilson(0, 100000)
    assert low == pytest.approx(0)
    assert high > 0


def test_structure_and_cooccurrence_use_draw_and_transition_denominators():
    draws = [
        {
            "issue": "2025001",
            "draw_date": "2025-01-02",
            "main_numbers": [1, 2, 3, 4, 5, 6],
            "special_numbers": [1],
        },
        {
            "issue": "2025002",
            "draw_date": "2025-01-05",
            "main_numbers": [1, 2, 3, 12, 23, 33],
            "special_numbers": [2],
        },
    ]
    result = summarize(draws, RULES["ssq"])
    assert [row["mean_per_draw"] for row in result["regions"]] == [4.5, 0.5, 1.0]
    assert result["structure"]["mean_span"] == 18.5
    assert result["structure"]["mean_repeated"] == 3
    assert result["structure"]["repeat_comparisons"] == 1
    assert result["structure"]["mean_high"] == 1
    assert result["structure"]["mean_consecutive_pairs"] == 3.5
    pairs = {tuple(row["numbers"]): row for row in result["cooccurrence"]}
    assert pairs[1, 2]["count"] == 2 and pairs[5, 6]["count"] == 1 and pairs[7, 8]["count"] == 0
    assert sum(row["count"] for row in pairs.values()) == 30
    assert pairs[1, 2]["expected_count"] == pytest.approx(2 * comb(31, 4) / comb(33, 6))
    assert summarize([], RULES["ssq"])["structure"]["mean_repeated"] is None


def test_simulation_reproducible_and_matches_known_distribution():
    result = simulate(RULES["ssq"], 100000, 42)
    assert result == simulate(RULES["ssq"], 100000, 42)
    assert result["mean_hits"] == pytest.approx(36 / 33, abs=0.012)
    assert sum(row["count"] for row in result["distribution"]) == 100000
    for row in result["distribution"]:
        assert abs(row["observed"] - row["theoretical"]) < 0.008


def test_randomness_has_calibrated_nonzero_monte_carlo_pvalues():
    data = synthetic_records("ssq", 50, 123)
    result = randomness(data, RULES["ssq"], trials=999, seed=42)
    for row in result["tests"][:3]:
        assert 0 < row["p_value"] <= 1
    assert all(row["adjusted_p_value"] >= row["p_value"] for row in result["tests"])
    assert result["correction"] == "bonferroni"
    # We deliberately do not demand non-significance on a finite random sample.


def test_cover_report_matches_independent_enumeration():
    pool = [1, 2, 3, 4, 5, 6, 7]
    result = optimize_cover(RULES["ssq"], pool, 2, 5, 42, 5000)
    tickets = [set(row["main_numbers"]) for row in result["tickets"]]
    outcomes = list(combinations(pool, 6))
    hits = sum(any(len(set(draw) & ticket) >= 5 for ticket in tickets) for draw in outcomes)
    assert result["conditional_main_coverage"] == hits / len(outcomes)
    assert result["conditional_draws_total"] == 7
    assert result["unconditional_main_coverage"] < result["conditional_main_coverage"]
    assert len({tuple(row["main_numbers"]) for row in result["tickets"]}) == 2
