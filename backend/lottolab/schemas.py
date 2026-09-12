from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from .domain import RULES, DatasetKind, Lottery

ModelId = Literal["uniform", "frequency", "logistic", "gradient_boosting"]


def default_models() -> list[ModelId]:
    return ["uniform", "frequency", "logistic", "gradient_boosting"]


class Scope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lottery: Lottery = "ssq"
    dataset_kind: DatasetKind = "real"
    seed: int = Field(default=2026, ge=0, le=2147483647)


class SyncRequest(Scope):
    count: int = Field(default=1000, ge=30, le=3000)

    @model_validator(mode="after")
    def real_only(self):
        if self.dataset_kind != "real":
            raise ValueError("公开数据同步只写入真实数据区")
        return self


class DemoRequest(Scope):
    dataset_kind: Literal["synthetic"] = "synthetic"
    count: int = Field(default=600, ge=100, le=3000)


class RandomnessRequest(Scope):
    window: int = Field(default=300, ge=30, le=1000)
    trials: int = Field(default=4999, ge=999, le=9999)


class BacktestRequest(Scope):
    models: list[ModelId] = Field(
        default_factory=default_models,
        min_length=1,
        max_length=4,
    )
    test_draws: int = Field(default=120, ge=20, le=400)
    training_window: int = Field(default=500, ge=80, le=1500)
    retrain_every: int = Field(default=20, ge=5, le=100)
    bootstrap_samples: int = Field(default=2000, ge=500, le=5000)

    @model_validator(mode="after")
    def unique_models(self):
        self.models = list(dict.fromkeys(["uniform", *self.models]))
        return self


class SimulationRequest(Scope):
    iterations: int = Field(default=100000, ge=1000, le=1000000)


class CoverRequest(Scope):
    candidate_numbers: list[StrictInt] = Field(
        default_factory=lambda: [1, 3, 5, 7, 9, 12, 15, 18, 22, 25, 29, 33], min_length=5, max_length=18
    )
    ticket_count: int = Field(default=10, ge=1, le=40)
    target_hits: int = Field(default=3, ge=1, le=6)
    samples: int = Field(default=20000, ge=5000, le=100000)

    @model_validator(mode="after")
    def legal_pool(self):
        rule = RULES[self.lottery]
        values = self.candidate_numbers
        if len(set(values)) != len(values) or len(values) < rule.main_count:
            raise ValueError("候选号码不能重复，且数量不能少于一注的主区数量")
        if any(v < 1 or v > rule.main_max for v in values) or self.target_hits > rule.main_count:
            raise ValueError("候选号码或目标命中数超出彩种范围")
        self.candidate_numbers.sort()
        return self


class TicketRequest(Scope):
    count: int = Field(default=5, ge=1, le=40)
    strategy: Literal["uniform", "frequency", "cold"] = "uniform"


class ResolutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["keep_existing", "accept_incoming"]
    expected_identity_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    expected_record_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
