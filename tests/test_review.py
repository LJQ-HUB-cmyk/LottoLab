"""预测复盘闭环单测：命中/奖级评分 + 台账登记 + 对账（无开奖则保持未核对）。"""

from datetime import date

from lottolab.db import Draw, PredictionLog
from lottolab.review import _score, log_predictions, next_issue, reconcile, review_summary, snapshot_review


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


def test_next_issue_increments_sequence():
    assert next_issue("2026108") == "2026109"
    assert next_issue("2026150") == "2026151"
    assert next_issue("26107") is None
    assert next_issue("") is None


def test_snapshot_review_logs_all_strategies_once(session_factory):
    online = [
        {
            "code": f"2026{i:03d}",
            "date": "2026-01-01",
            "red": ["01", "02", "03", "04", "05", "06"],
            "blue": ["07"],
        }
        for i in range(101, 161)
    ]
    with session_factory() as s:
        first = snapshot_review(s, "ssq", online, 20260919)
        assert first["logged"] == 7 and first["target_issue"] == "2026161"
        again = snapshot_review(s, "ssq", online, 20260919)
        assert again["logged"] == 0 and "skipped" in again  # 幂等跳过
        summary = review_summary(s, "ssq")
        assert summary["logged"] == 7 and summary["checked"] == 0


def test_snapshot_review_without_data(session_factory):
    with session_factory() as s:
        result = snapshot_review(s, "ssq", [], 20260919)
        assert result["logged"] == 0 and "skipped" in result
