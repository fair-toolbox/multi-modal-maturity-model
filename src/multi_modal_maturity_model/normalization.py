"""Metric normalization for maturity analysis."""

import logging
import math
from typing import Any

from .config import MetricsConfig, MetricSpec

logger = logging.getLogger(__name__)


def normalize_boolean(value: bool) -> float:
    return float(value)


def normalize_fraction(value: float) -> float:
    return max(0.0, min(1.0, value))


def normalize_clamp(value: float, lo: float, hi: float, invert: bool = False) -> float:
    clamped = max(lo, min(hi, value))
    score = (clamped - lo) / (hi - lo) if hi > lo else 0.0
    return 1.0 - score if invert else score


def normalize_log(value: float, cap: float, invert: bool = False) -> float:
    v = max(0.0, min(cap, value))
    result = math.log1p(v) / math.log1p(cap)
    return 1.0 - result if invert else result


def normalize_metric(
    metric_name: str,
    raw_value: Any,
    metric_spec: MetricSpec,
) -> float | None:
    """
    Normalize a single metric value using its configuration.

    Parameters
    ----------
    metric_name : str
        Name of the metric (for logging)
    raw_value : Any
        Raw value of the metric
    metric_spec : MetricSpec
        Metric specification from metrics.yaml

    Returns
    -------
    float | None
        Normalized value in [0, 1] range, or None if value is missing
        or normalization fails
    """
    if raw_value is None:
        logger.debug(
            f"[{metric_name}] No extracted value found, skipping normalization"
        )
        return None

    norm_cfg = metric_spec.normalization

    if isinstance(raw_value, bool):
        return normalize_boolean(raw_value)

    if not norm_cfg:
        logger.debug(
            f"[{metric_name}] No normalization config found, returning raw value"
        )
        return raw_value

    scaler = norm_cfg.scaler

    try:
        if scaler == "clamp":
            return normalize_clamp(
                raw_value, lo=norm_cfg.lo, hi=norm_cfg.hi, invert=norm_cfg.invert
            )

        elif scaler == "log":
            return normalize_log(raw_value, cap=norm_cfg.cap, invert=norm_cfg.invert)

        elif scaler == "fraction":
            return normalize_fraction(raw_value)

    except (TypeError, ValueError) as e:
        logger.error(f"[{metric_name}] Error normalizing value {raw_value}: {e}")
        return None


def normalize_all(
    extracted_metrics: dict[str, Any],
    metrics_cfg: MetricsConfig,
) -> dict[str, float]:
    """
    Normalize all extracted metrics to [0, 1] scale.

    Parameters
    ----------
    extracted_metrics : dict[str, Any]
        Dictionary of extracted metrics by metric name
    metrics_cfg : MetricsConfig
        Metrics configuration from metrics.yaml

    Returns
    -------
    dict[str, float]
        Dictionary of normalized metrics by metric name
    """
    normalized = {}

    for metric_name, raw_value in extracted_metrics:
        metric_spec = metrics_cfg[metric_name]
        normalized_value = normalize_metric(metric_name, raw_value, metric_spec)

        # Only include non-None values in result
        if normalized_value is not None:
            normalized[metric_name] = normalized_value

    return normalized
