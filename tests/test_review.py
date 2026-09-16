"""预测复盘闭环单测：命中/奖级评分 + 台账登记 + 对账（无开奖则保持未核对）。"""

from datetime import date

from lottolab.db import Draw, PredictionLog
from lottolab.review import _score, log_predictions, reconcile, review_summary


def test_score_pool_ssq_tier():
    pred = PredictionLog(kind="ssq", main_numbers=[1, 2, 3, 4, 5, 6], special_numbers=[7])
    draw = Draw(
        lottery="ssq",
        issue="x",
        draw_date=date(2026, 1, 1),
        main_numbers=[1, 2, 3, 10, 11, 12],
        special_numbers=[7],
    )
    hit_main, hit_special, prize = _score("ssq", pred, draw)
    assert hit_main == 3 and hit_special == 1 and prize == "5"  # 3红+蓝 → 五等奖


def test_score_digit_full_hit():
    pred = PredictionLog(kind="fc3d", main_numbers=[1, 2, 3], special_numbers=[])
    draw = Draw(
        lottery="fc3d", issue="x", draw_date=date(2026, 1, 1), main_numbers=[1, 2, 3], special_numbers=[]
    )
    hit_main, _, prize = _score("fc3d", pred, draw)
    assert hit_main == 3 and prize == "全中"


def test_review_reconcile_waits_for_draw(session_factory):
    with session_factory() as s:
        n = log_predictions(
            s, "ssq", "2099001", [{"strategy": "稳健·热号", "main": [1, 2, 3, 4, 5, 6], "aux": [7]}]
        )
        assert n == 1
        assert reconcile(s, "ssq") == 0  # 该期未开奖 → 不对账
        summary = review_summary(s, "ssq")
        assert summary["logged"] == 1 and summary["checked"] == 0
