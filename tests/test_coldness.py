"""fit_coldness 闸门测试：销量协变量 + 70/30 时序样本外 + 安慰剂 fail-closed。"""

import random

from lottolab.coldness import _features, build_fit_rows, fit_coldness


def make_rows(seed=7, count=1200, effects=None, placebo_effects=None, flip_at=None):
    """合成拟合行：n1 = 8 × Πmult^feat × (sales/3e8)^0.8 × 噪声。

    effects 作用于全段；flip_at 之后 effects 取倒数（模拟样本外反号）；
    placebo(n2) 默认只跟销量走，placebo_effects 让安慰剂也带特征效应（模拟混淆）。
    """
    rng = random.Random(seed)
    effects = effects or {}
    placebo_effects = placebo_effects or {}
    rows = []
    for i in range(count):
        red = sorted(rng.sample(range(1, 34), 6))
        blue = rng.randint(1, 16)
        f = _features("ssq", red, [blue])
        eff = {k: 1 / v for k, v in effects.items()} if flip_at is not None and i >= flip_at else effects
        mult = 1.0
        for k, m in eff.items():
            if f.get(k):
                mult *= m
        sales = rng.uniform(2.5e8, 4.0e8)
        n1 = max(0, round(8 * mult * (sales / 3e8) ** 0.8 * rng.uniform(0.7, 1.3)))
        pmult = 1.0
        for k, m in placebo_effects.items():
            if f.get(k):
                pmult *= m
        n2 = max(0, round(200 * pmult * (sales / 3e8) * rng.uniform(0.7, 1.3)))
        rows.append(
            {
                "main_numbers": red,
                "special_numbers": [blue],
                "winner_count_1": n1,
                "sales": sales,
                "n2": n2,
            }
        )
    return rows


def test_fit_recovers_effects_with_sales_control():
    result = fit_coldness("ssq", make_rows(effects={"allLe31": 1.2, "blueHot": 1.25}))
    assert result["ok"] is True, result
    assert result["n"] == 1200 and result["n_train"] == 840 and result["n_test"] == 360
    assert abs(result["multipliers"]["allLe31"] - 1.2) < 0.1
    assert abs(result["multipliers"]["blueHot"] - 1.25) < 0.1
    assert result["placebo"]["pass"] is True


def test_fit_rejects_on_placebo_confounding():
    result = fit_coldness(
        "ssq",
        make_rows(effects={"blueHot": 1.25}, placebo_effects={"blueHot": 1.3}),
    )
    assert result["ok"] is False
    assert "安慰剂" in result["reason"]


def test_fit_rejects_without_placebo_column():
    rows = make_rows(count=300)
    for r in rows:
        del r["n2"]
    result = fit_coldness("ssq", rows)
    assert result["ok"] is False
    assert "安慰剂" in result["reason"]


def test_fit_rejects_small_sample():
    result = fit_coldness("ssq", make_rows(count=100))
    assert result["ok"] is False
    assert result["reason"] == "样本不足"


def test_fit_drops_sign_flipped_feature():
    result = fit_coldness("ssq", make_rows(effects={"blueHot": 1.3}, flip_at=840))
    assert "blueHot" in result["dropped"]
    assert "blueHot" not in result.get("multipliers", {})


def test_build_fit_rows_requires_all_three_columns():
    draws = [
        {
            "issue": "2026101",
            "main_numbers": [1, 2, 3, 4, 5, 6],
            "special_numbers": [7],
            "sales": "300000000.00",
            "prizes": {"winner_count_1": "5"},
        },
        {
            "issue": "2026102",  # 无安慰剂 → 丢行
            "main_numbers": [1, 2, 3, 4, 5, 6],
            "special_numbers": [7],
            "sales": "300000000.00",
            "prizes": {"winner_count_1": "5"},
        },
        {
            "issue": "2026103",  # 无一等奖注数 → 丢行
            "main_numbers": [1, 2, 3, 4, 5, 6],
            "special_numbers": [7],
            "sales": "300000000.00",
            "prizes": {},
        },
    ]
    rows = build_fit_rows(draws, {"2026101": 100, "2026103": 100})
    assert len(rows) == 1 and rows[0]["n2"] == 100 and rows[0]["winner_count_1"] == "5"
