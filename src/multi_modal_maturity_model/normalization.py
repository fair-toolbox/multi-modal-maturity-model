"""Metric normalization for maturity analysis."""

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


def normalize_boolean(value: bool) -> float:
    return 1.0 if value else 0.0


def normalize_fraction(value: float) -> float:
    return max(0.0, min(1.0, value))


def normalize_clamp(value: float, lo: float, hi: float, invert: bool = False) -> float:
    """
    Linear scaling between bounds with optional inversion.
    """
    clamped = max(lo, min(hi, value))

    if hi == lo:
        normalized = 0.0
    else:
        normalized = (clamped - lo) / (hi - lo)

    if invert:
        normalized = 1.0 - normalized

    return normalized


def normalize_log(value: float, cap: float) -> float:
    """
    Logarithmic scaling with cap.
    """
    if value <= 0:
        return 0.0

    capped = min(value, cap)
    normalized = math.log(1 + capped) / math.log(1 + cap)

    return normalized


def _extract_value_from_sources(sources_dict: dict[str, Any]) -> Any:
    """
    Extract single value from sources dictionary.
    """
    if not sources_dict:
        return None

    # One source per metric
    values = list(sources_dict.values())
    return values[0] if values else None


def normalize_metric(
    metric_name: str,
    sources_dict: dict[str, Any],
    metric_cfg: dict[str, Any],
) -> float | None:
    """
    Normalize a single metric value using its configuration.

    Parameters
    ----------
    metric_name : str
        Name of the metric (for logging)
    sources_dict : dict[str, Any]
        Dictionary mapping source names to values, e.g., {'github': 50}
    metric_cfg : dict[str, Any]
        Metric configuration from metrics.yaml

    Returns
    -------
    float | None
        Normalized value in [0, 1] range, or None if value is missing
        or normalization fails
    """
    # Extract single value from sources
    raw_value = _extract_value_from_sources(sources_dict)

    if raw_value is None:
        return None

    # Get normalization config
    norm_cfg = metric_cfg.get("normalization")

    if not norm_cfg:
        logger.debug(
            f"[{metric_name}] No normalization config found, returning raw value"
        )
        return raw_value

    scaler = norm_cfg.get("scaler")

    try:
        if scaler == "clamp":
            lo = norm_cfg.get("lo", 0.0)
            hi = norm_cfg.get("hi", 1.0)
            invert = norm_cfg.get("invert", False)
            return normalize_clamp(raw_value, lo=lo, hi=hi, invert=invert)

        elif scaler == "log":
            cap = norm_cfg.get("cap", 100)
            return normalize_log(raw_value, cap=cap)

        elif scaler == "fraction":
            return normalize_fraction(raw_value)

        else:
            if isinstance(raw_value, bool):
                return normalize_boolean(raw_value)

            logger.warning(
                f"[{metric_name}] Unknown scaler type '{scaler}', returning raw value"
            )
            return raw_value

    except (TypeError, ValueError) as e:
        logger.error(f"[{metric_name}] Error normalizing value {raw_value}: {e}")
        return None


def normalize_metrics(
    extracted_metrics: dict[str, dict[str, Any]],
    metrics_cfg: dict[str, dict[str, Any]],
) -> dict[str, float]:
    """
    Normalize all extracted metrics to [0, 1] scale.

    Parameters
    ----------
    extracted_metrics : dict[str, dict[str, Any]]
        Extracted metrics from extract_all_metrics(), format:
        {metric_name: {source_name: raw_value}}
    metrics_cfg : dict[str, dict[str, Any]]
        Metrics configuration from metrics.yaml (top-level 'metrics' dict)

    Returns
    -------
    dict[str, float]
        Flat dictionary of normalized values:
        {metric_name: normalized_value}
    """
    normalized = {}

    for metric_name, sources_dict in extracted_metrics.items():
        # Get metric configuration
        metric_cfg = metrics_cfg.get(metric_name, {})

        # Normalize the metric
        normalized_value = normalize_metric(metric_name, sources_dict, metric_cfg)

        # Only include non-None values in result
        if normalized_value is not None:
            normalized[metric_name] = normalized_value

    return normalized
