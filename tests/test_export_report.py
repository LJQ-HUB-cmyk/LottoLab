"""export_report.py 单测：用最小伪造结果验证摘要渲染（经 importlib 加载脚本）。"""

import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "export_report", Path(__file__).resolve().parents[1] / "scripts" / "export_report.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

FAKE = {
    "config": {
        "lottery": "ssq",
        "dataset_kind": "real",
        "training_window": 500,
        "retrain_every": 20,
        "seed": 2026,
    },
    "sample_size": 120,
    "start_issue": "2026001",
    "end_issue": "2026120",
    "primary_metric": "主区逐号码平均二元 Brier",
    "comparison_method": "块 bootstrap",
    "stability_method": "前后半对照",
    "feature_version": "v1",
    "code_fingerprint": "abc123",
    "models": [
        {
            "model": "uniform",
            "name": "均匀随机",
            "verdict": "BASELINE",
            "cost": "240.00",
            "gross": None,
            "roi": None,
            "missing_settlements": 120,
            "metrics": {"main_brier": 0.15, "main_hits": 1.1},
            "comparison": None,
            "stability": None,
        },
        {
            "model": "frequency",
            "name": "历史频率",
            "verdict": "NOT_SIGNIFICANT",
            "cost": "240.00",
            "gross": "100.00",
            "roi": -0.58,
            "missing_settlements": 0,
            "metrics": {"main_brier": 0.149, "main_hits": 1.12},
            "comparison": {"delta": 0.001, "confidence_interval": [-0.002, 0.004], "adjusted_p_value": 0.4},
            "stability": {"verdict": "INCONSISTENT", "first_half": 0.003, "second_half": -0.001, "n": 120},
        },
    ],
    "limitations": ["95% 区间是名义区间。"],
}


def test_render_covers_models_verdicts_and_stability():
    text = MODULE.render_markdown(FAKE)
    assert "# 回测报告：ssq / real" in text
    assert "均匀随机" in text and "BASELINE" in text
    assert "前后半不一致" in text
    assert "未计算" in text  # uniform 无 ROI
    assert "-58.00%" in text
    assert "95% 区间是名义区间。" in text
    assert "abc123" in text
    assert "不构成购彩建议" in text


def test_render_handles_empty_models():
    text = MODULE.render_markdown({"config": {}, "models": [], "limitations": []})
    assert "# 回测报告" in text
