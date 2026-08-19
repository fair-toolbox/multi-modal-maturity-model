"""Dimension and overall maturity scoring."""

import logging
from typing import Any

from .config import WeightsConfig, WeightMap

logger = logging.getLogger(__name__)


def weighted_average(
    values: dict[str, float], weights: WeightMap | dict[str, float]
) -> float | None:
    """
    Compute the weighted average over whichever keys in `weights` are also present in `values`. Missing keys are skipped and the result is renormalized against the weight actually present.

    Parameters
    ----------
    values : dict[str, float]
        Available scores keyed by metric or dimension name.
    weights : WeightMap | dict[str, float]
        (name, weight) pairs.

    Returns
    -------
    float | None
        Weighted average, or None if no valid values are provided.
    """
    present = [(name, weight) for name, weight in weights.items() if name in values]

    if not present:
        return None

    weight_sum = sum(weight for _, weight in present)
    if weight_sum == 0:
        return None

    return sum(values[name] * weight for name, weight in present) / weight_sum


def score_dimensions(
    normalized_metrics: dict[str, float],
    weights_cfg: WeightsConfig,
) -> dict[str, float | None]:
    """
    Score each dimension using the weighted average of its metrics.
    """
    scores = {}
    for dim_name, weight_map in weights_cfg.dimensions.items():
        score = weighted_average(normalized_metrics, weight_map)
        if score is None:
            logger.warning(
                f"No valid metrics found for dimension '{dim_name}', skipping scoring."
            )
        scores[dim_name] = score
    return scores


def score_overall(
    dimension_scores: dict[str, float | None],
    weights_cfg: WeightsConfig,
) -> float | None:
    """
    Score overall maturity using the weighted average of dimension scores.
    """
    available = {
        dim: score for dim, score in dimension_scores.items() if score is not None
    }
    return weighted_average(available, weights_cfg.overall)


def score_all(
    normalized_metrics: dict[str, float],
    weights_cfg: WeightsConfig,
) -> dict[str, Any]:
    """
    Score all dimensions and overall maturity.

    Returns
    -------
    dict[str, Any]
        A dictionary containing the scores for each dimension and the overall score.
    """
    dimension_scores = score_dimensions(normalized_metrics, weights_cfg)
    overall_score = score_overall(dimension_scores, weights_cfg)
    return {"dimensions": dimension_scores, "overall": overall_score}
