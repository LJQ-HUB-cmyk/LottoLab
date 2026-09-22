"""回测 JSON 导出 → 可引用的 Markdown 摘要（输出到控制台，自行重定向保存）。

输入为页面“导出完整报告”下载的 JSON（即 run_backtest 返回结构）。
本脚本只做摘要渲染，不重算、不挑选：显著与否以 JSON 内 verdict 为准。
报告描述历史样本，不构成对未来的保证；生成物建议放 .local/，不要提交进仓库。
"""

import argparse
import json
import sys
from pathlib import Path

STABILITY_CN = {"CONSISTENT": "前后半一致", "INCONSISTENT": "前后半不一致", "TOO_SHORT": "样本不足"}


def _fmt(value, digits=5):
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def render_markdown(result: dict) -> str:
    config = result.get("config", {})
    lines = [
        f"# 回测报告：{config.get('lottery', '?')} / {config.get('dataset_kind', '?')}",
        "",
        f"- 测试期数：{result.get('sample_size')}（{result.get('start_issue')} 至 {result.get('end_issue')}）",
        f"- 训练窗口：{config.get('training_window')}，重训练间隔：{config.get('retrain_every')}，种子：{config.get('seed')}",
        f"- 主指标：{result.get('primary_metric', '')}",
        f"- 比较方法：{result.get('comparison_method', '')}",
        f"- 稳定性：{result.get('stability_method', '')}",
        f"- 特征版本：{result.get('feature_version', '')}，代码指纹：`{result.get('code_fingerprint', '')}`",
        "",
        "| 模型 | 主区 Brier | 平均命中 | 优势与 95% 区间 | 校正后 p 值 | 判定 | 前后半对照 |",
        "| :--- | ---: | ---: | :--- | ---: | :--- | :--- |",
    ]
    for m in result.get("models", []):
        comp = m.get("comparison") or {}
        ci = comp.get("confidence_interval") or []
        ci_text = f"[{', '.join(_fmt(v) for v in ci)}]" if ci else "—"
        stab = m.get("stability") or {}
        halves = stab.get("first_half"), stab.get("second_half")
        if halves[0] is None:
            stab_text = STABILITY_CN.get(stab.get("verdict"), "—")
        else:
            stab_text = (
                f"{STABILITY_CN.get(stab.get('verdict'), '?')}（{_fmt(halves[0])} / {_fmt(halves[1])}）"
            )
        roi = m.get("roi")
        roi_text = f"{roi:.2%}" if isinstance(roi, (int, float)) else "未计算"
        lines.append(
            f"| {m.get('name')} | {_fmt((m.get('metrics') or {}).get('main_brier'))} "
            f"| {_fmt((m.get('metrics') or {}).get('main_hits'), 3)} "
            f"| {_fmt(comp.get('delta'))} {ci_text} | {_fmt(comp.get('adjusted_p_value'))} "
            f"| {m.get('verdict')} | {stab_text} |"
        )
        lines.append(
            f"  - 成本 {m.get('cost')} / 毛派奖 {m.get('gross')} / ROI {roi_text} / 未结算 {m.get('missing_settlements')}"
        )
    lines += ["", "## 使用边界", ""]
    for item in result.get("limitations", []):
        lines.append(f"- {item}")
    lines += ["", "> 本报告只描述历史样本，不改变任何一注的中奖概率，不构成购彩建议。"]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="回测 JSON 导出转 Markdown 摘要")
    parser.add_argument("input", help="导出的回测 JSON 文件路径（- 为 stdin）")
    parser.add_argument("-o", "--output", default="", help="输出路径，缺省打印到控制台")
    args = parser.parse_args()
    raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    text = render_markdown(json.loads(raw))
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
