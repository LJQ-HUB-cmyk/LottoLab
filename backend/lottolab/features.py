"""Every row is a snapshot of strictly earlier draws."""

from collections import deque

import numpy as np

from .domain import Rule

FEATURE_NAMES = [
    "frequency_10",
    "frequency_30",
    "frequency_100",
    "frequency_all",
    "omission_capped",
    "appeared_last",
    "appeared_previous",
    "number_position",
]
FEATURE_VERSION = "causal-number-features-v1"


def causal_features(draws: list[dict], rule: Rule, area: str = "main") -> tuple[np.ndarray, np.ndarray]:
    keys = [(row["draw_date"], row["issue"]) for row in draws]
    if keys != sorted(keys):
        raise ValueError("特征输入必须按开奖时间升序排列")
    maximum, chosen, field = (
        (rule.main_max, rule.main_count, "main_numbers")
        if area == "main"
        else (rule.special_max, rule.special_count, "special_numbers")
    )
    if maximum == 0 or chosen == 0:  # 空区域（如快乐8 无附加区）→ 返回空特征，避免除零
        return np.zeros((len(draws), 0, len(FEATURE_NAMES))), np.zeros((len(draws), 0))
    prior = chosen / maximum
    counts = np.zeros(maximum)
    last_seen = np.full(maximum, -1)
    recent: deque = deque(maxlen=100)
    features = np.zeros((len(draws), maximum, len(FEATURE_NAMES)))
    labels = np.zeros((len(draws), maximum))
    for t, draw in enumerate(draws):
        # Snapshot first. The current outcome is not read until features[t] is complete.
        for column, window in enumerate((10, 30, 100)):
            history = list(recent)[-window:]
            features[t, :, column] = (
                (np.sum(history, axis=0) + 2 * prior) / (len(history) + 2) if history else prior
            )
        features[t, :, 3] = (counts + 2 * prior) / (t + 2)
        features[t, :, 4] = np.minimum(t - 1 - last_seen, 100) / 100
        features[t, :, 5] = recent[-1] if recent else 0
        features[t, :, 6] = recent[-2] if len(recent) > 1 else 0
        features[t, :, 7] = np.arange(1, maximum + 1) / maximum
        current = np.zeros(maximum)
        current[np.asarray(draw[field], dtype=int) - 1] = 1
        labels[t] = current
        counts += current
        last_seen[current == 1] = t
        recent.append(current)
    return features, labels


def coherent_marginals(probabilities: np.ndarray, chosen: int) -> np.ndarray:
    """Cardinality projection, not a claim of empirical probability calibration."""
    raw = np.clip(np.asarray(probabilities, dtype=float), 1e-9, 1 - 1e-9)
    logits = np.log(raw / (1 - raw))
    low, high = -50.0, 50.0
    for _ in range(70):
        shift = (low + high) / 2
        result = 1 / (1 + np.exp(-(logits + shift)))
        if result.sum() < chosen:
            low = shift
        else:
            high = shift
    return 1 / (1 + np.exp(-(logits + (low + high) / 2)))


def choose_top(probabilities: np.ndarray, count: int, rng) -> list[int]:
    order = np.lexsort((rng.random(len(probabilities)), -probabilities))
    return sorted(int(n) + 1 for n in order[:count])
