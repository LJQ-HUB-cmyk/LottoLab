from datetime import date, timedelta

import pytest
from lottolab.domain import RULES, DrawInput, dlt_prize_tier, ssq_prize_tier
from pydantic import ValidationError


def test_number_spaces():
    assert RULES["ssq"].combinations == 17721088
    assert RULES["dlt"].combinations == 21425712


@pytest.mark.parametrize(
    "change",
    [
        {"main_numbers": [2, 2, 13, 14, 15, 30]},
        {"main_numbers": [0, 4, 13, 14, 15, 30]},
        {"main_numbers": [2, 4, 13, 14, 15, 34]},
        {"main_numbers": [2, 4, 13, 14, 15]},
        {"main_numbers": [True, 4, 13, 14, 15, 30]},
        {"main_numbers": [2.0, 4, 13, 14, 15, 30]},
        {"special_numbers": [17]},
        {"issue": "2025105"},
        {"issue": "2026000"},
        {"sales": "-1"},
        {"pool_amount": "NaN"},
        {"sales": "1.001"},
        {"draw_date": (date.today() + timedelta(days=10)).isoformat()},
    ],
)
def test_invalid_draws_rejected(raw_draw, change):
    with pytest.raises(ValidationError):
        DrawInput.model_validate({**raw_draw, **change})


def test_sorting_and_dlt_rule(raw_draw):
    draw = DrawInput.model_validate({**raw_draw, "main_numbers": [30, 15, 14, 13, 4, 2]})
    assert draw.main_numbers == [2, 4, 13, 14, 15, 30]
    dlt = DrawInput.model_validate(
        {**raw_draw, "lottery": "dlt", "main_numbers": [1, 5, 12, 20, 35], "special_numbers": [12, 2]}
    )
    assert dlt.special_numbers == [2, 12]


def test_synthetic_namespace_is_explicit(raw_draw):
    with pytest.raises(ValidationError):
        DrawInput.model_validate({**raw_draw, "dataset_kind": "synthetic"})
    assert (
        DrawInput.model_validate({**raw_draw, "dataset_kind": "synthetic", "issue": "SIM-00001"}).dataset_kind
        == "synthetic"
    )


@pytest.mark.parametrize(
    "hits,tier",
    [
        ((6, 1), "1"),
        ((6, 0), "2"),
        ((5, 1), "3"),
        ((4, 1), "4"),
        ((3, 1), "5"),
        ((0, 1), "6"),
        ((3, 0), None),
    ],
)
def test_ssq_grade(hits, tier):
    assert ssq_prize_tier(*hits) == tier


def test_dlt_grade():
    assert dlt_prize_tier(5, 2) == "1"
    assert dlt_prize_tier(2, 2) == "8"
    assert dlt_prize_tier(0, 2) == "9"
    assert dlt_prize_tier(2, 0) is None
