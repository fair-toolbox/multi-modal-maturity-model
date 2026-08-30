"""Dimension and overall scoring with per-metric contribution reporting."""

from typing import Any
from pydantic import BaseModel

from .config import WeightMap, WeightsConfig


class MetricContribution(BaseModel):
    """How a single metric contributed to its dimension's score."""

    metric: str
    raw_value: Any | None
    normalized_value: float | None
    weight: float
    contribution: float


class DimensionScore(BaseModel):
    dimension: str
    score: float | None
    metrics: list[MetricContribution]


class ScoringResult(BaseModel):
    overall_score: float | None
    dimensions: list[DimensionScore]


def _weighted_average(
    values: dict[str, float | None], weights: dict[str, float]
) -> tuple[float | None, dict[str, float]]:
    """
    Compute a weighted average over available (non-None) values.

    Weights are renormalized to sum to 1.0 across only the available entries;
    unavailable entries get an effective weight of 0.0.

    Returns
    -------
    tuple[float | None, dict[str, float]]
        The weighted average (None if no values are available) and a mapping
        of key -> effective weight actually used in the computation.
    """
    available_weight = sum(
        weights[key] for key, value in values.items() if value is not None
    )

    if available_weight <= 0:
        return None, {key: 0.0 for key in weights}

    effective_weights = {
        key: (weights[key] / available_weight if values.get(key) is not None else 0.0)
        for key in weights
    }
    score = sum(
        effective_weights[key] * value
        for key, value in values.items()
        if value is not None
    )
    return score, effective_weights


def _score_dimension(
    dimension: str,
    weight_map: WeightMap,
    extracted_metrics: dict[str, Any],
    normalized_metrics: dict[str, float | None],
) -> DimensionScore:
    values = {metric: normalized_metrics.get(metric) for metric in weight_map}
    score, effective_weights = _weighted_average(values, weight_map)

    metrics = [
        MetricContribution(
            metric=metric,
            raw_value=extracted_metrics.get(metric),
            normalized_value=values[metric],
            weight=effective_weights[metric],
            contribution=(
                effective_weights[metric] * values[metric]
                if values[metric] is not None
                else 0.0
            ),
        )
        for metric in weight_map
    ]
    return DimensionScore(dimension=dimension, score=score, metrics=metrics)


def score_all(
    extracted_metrics: dict[str, Any],
    normalized_metrics: dict[str, float | None],
    weights_cfg: WeightsConfig,
) -> ScoringResult:
    """
    Compute per-dimension and overall maturity scores from normalized metrics.

    Parameters
    ----------
    extracted_metrics : dict[str, Any]
        Raw metric values by metric name, as produced by MetricExtractor.
    normalized_metrics : dict[str, float | None]
        Normalized metric values ([0, 1]) by metric name, as produced by
        normalize_all. None indicates the metric could not be computed.
    weights_cfg : WeightsConfig
        Dimension and overall weight configuration from weights.yaml.

    Returns
    -------
    ScoringResult
        Overall score and per-dimension breakdowns, each listing how every
        configured metric contributed (raw value, normalized value, the
        effective weight after excluding unavailable metrics, and its
        resulting contribution to the dimension score).
    """
    dimensions = [
        _score_dimension(
            dimension_name,
            weight_map,
            extracted_metrics,
            normalized_metrics,
        )
        for dimension_name, weight_map in weights_cfg.dimensions.items()
    ]

    dimension_scores = {
        dimension.dimension: dimension.score for dimension in dimensions
    }
    overall_score, _ = _weighted_average(
        dimension_scores, dict(weights_cfg.overall.items())
    )

    return ScoringResult(overall_score=overall_score, dimensions=dimensions)
