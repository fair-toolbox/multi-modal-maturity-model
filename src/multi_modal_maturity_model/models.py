from dataclasses import dataclass


@dataclass
class DimensionScore:
    name: str
    score: float | None
    coverage: float  # fraction of configured metrics that were available
    contributing_metrics: list[str]


@dataclass
class MaturityProfile:
    overall_score: float | None
    dimensions: dict[str, DimensionScore]
    metrics: dict[str, float]
