import copy

import numpy as np
import pytest
from lottolab.backtest import run_backtest
from lottolab.domain import RULES
from lottolab.features import causal_features, coherent_marginals
from lottolab.ingestion import synthetic_records
from lottolab.schemas import BacktestRequest


def test_current_and_future_outcomes_cannot_change_earlier_features():
    original = synthetic_records("ssq", 150, 92)
    changed = copy.deepcopy(original)
    for row in changed[100:]:
        row["main_numbers"] = [1, 2, 3, 4, 5, 6]
        row["special_numbers"] = [16]
    for area in ("main", "special"):
        before, _ = causal_features(original, RULES["ssq"], area)
        after, _ = causal_features(changed, RULES["ssq"], area)
        np.testing.assert_array_equal(before[:101], after[:101])
        assert not np.array_equal(before[101:], after[101:])
        prefix, _ = causal_features(original[:101], RULES["ssq"], area)
        np.testing.assert_array_equal(before[:101], prefix)


def test_postdraw_financial_metadata_not_used_as_features():
    original = synthetic_records("ssq", 100, 1)
    changed = copy.deepcopy(original)
    for row in changed:
        row["prizes"] = {"1": "99999999"}
        row["sales"] = "1234"
    np.testing.assert_array_equal(
        causal_features(original, RULES["ssq"])[0], causal_features(changed, RULES["ssq"])[0]
    )


@pytest.mark.parametrize("count,size", [(6, 33), (1, 16), (5, 35), (2, 12)])
def test_probability_output_has_correct_cardinality(count, size):
    p = coherent_marginals(np.linspace(0.0001, 0.999, size), count)
    assert p.sum() == pytest.approx(count, abs=1e-10)
    assert np.all((p > 0) & (p < 1))


def test_walk_forward_models_do_not_see_current_or_future_test_labels():
    data = synthetic_records("ssq", 120, 94)
    changed = copy.deepcopy(data)
    for row in changed[110:]:
        row["main_numbers"] = [1, 2, 3, 4, 5, 6]
        row["special_numbers"] = [1]
    config = BacktestRequest(
        dataset_kind="synthetic",
        models=["uniform", "frequency", "logistic", "gradient_boosting"],
        test_draws=20,
        training_window=80,
        retrain_every=10,
        bootstrap_samples=500,
    )
    first = run_backtest(data, RULES["ssq"], config)
    second = run_backtest(changed, RULES["ssq"], config)
    for model in config.models:
        for a, b in zip(first["records"][model][:11], second["records"][model][:11], strict=True):
            np.testing.assert_array_equal(a["main_probabilities"], b["main_probabilities"])
            np.testing.assert_array_equal(a["special_probabilities"], b["special_probabilities"])
    for model in first["models"]:
        assert model["roi"] is None
        assert sum(bucket["count"] for bucket in model["calibration"]) == 20 * 33


def test_model_predictions_do_not_depend_on_other_models_selected():
    data = synthetic_records("ssq", 120, 94)
    settings = {
        "dataset_kind": "synthetic",
        "test_draws": 20,
        "training_window": 80,
        "bootstrap_samples": 500,
    }
    first = run_backtest(data, RULES["ssq"], BacktestRequest(models=["uniform", "frequency"], **settings))
    second = run_backtest(
        data, RULES["ssq"], BacktestRequest(models=["uniform", "logistic", "frequency"], **settings)
    )
    assert first["records"]["frequency"] == second["records"]["frequency"]
