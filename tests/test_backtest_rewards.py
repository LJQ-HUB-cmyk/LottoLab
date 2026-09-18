"""DLT 收益结算：规则版本分界 + 当期奖金优先 + 固定奖常量回退。"""

from decimal import Decimal

from lottolab.backtest import run_backtest, settle_reward
from lottolab.domain import RULES
from lottolab.ingestion import synthetic_records
from lottolab.schemas import BacktestRequest


def test_settle_ssq_keeps_history_behavior():
    assert settle_reward("ssq", "real", {"prizes": {}}, 0, 0) == (Decimal(0), True)
    hit = {"prizes": {"4": "200"}}
    assert settle_reward("ssq", "real", hit, 5, 0) == (Decimal(200), True)
    assert settle_reward("ssq", "real", {"prizes": {}}, 5, 0) == (None, False)
    assert settle_reward("ssq", "synthetic", hit, 5, 0) == (None, False)
    assert settle_reward("qlc", "real", hit, 5, 0) == (None, False)


def test_settle_dlt_uses_prizes_first_then_era_fixed():
    new = {"draw_date": "2026-01-01", "prizes": {}}
    assert settle_reward("dlt", "real", new, 5, 0) == (Decimal(10000), True)
    assert settle_reward("dlt", "real", new, 5, 2) == (None, False)  # 新规则浮动无数则未结算
    with_prizes = {"draw_date": "2026-01-01", "prizes": {"1": "8000000"}}
    assert settle_reward("dlt", "real", with_prizes, 5, 2) == (Decimal(8000000), True)
    old = {"draw_date": "2018-01-01", "prizes": {}}
    assert settle_reward("dlt", "real", old, 4, 2) == (None, False)  # 旧规则三等浮动
    assert settle_reward("dlt", "real", old, 4, 1) == (Decimal(200), True)  # 旧规则四等固定


def test_dlt_backtest_reports_roi_with_complete_prizes():
    draws = synthetic_records("dlt", 120, seed=11)
    prizes = {
        t: str(a)
        for t, a in zip(
            ("1", "2", "3", "4", "5", "6", "7", "8", "9"),
            (10000000, 200000, 10000, 3000, 300, 200, 100, 15, 5),
            strict=True,
        )
    }
    for d in draws:
        d["prizes"] = dict(prizes)
    config = BacktestRequest(
        lottery="dlt",
        dataset_kind="real",
        test_draws=20,
        training_window=80,
        retrain_every=10,
        bootstrap_samples=500,
        models=["uniform", "frequency"],
        seed=7,
    )
    result = run_backtest(draws, RULES["dlt"], config)
    for model in result["models"]:
        assert model["missing_settlements"] == 0
        assert model["roi"] is not None and model["gross"] is not None
        assert Decimal(model["cost"]) == Decimal("2") * 20
