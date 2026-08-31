"""
Loader for configuration files (weights, metrics, patterns).
Validates the files, including cross-references between them.
"""

from __future__ import annotations

import yaml

from importlib import resources
from pathlib import Path
from typing import Any

from .schema import MetricsConfig, PatternsConfig, WeightsConfig


class ConfigError(Exception):
    """Custom exception for configuration errors."""


def _read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _default_config_name(filename: str) -> Path:
    return Path(resources.files("multi_modal_maturity_model.config.default") / filename)


def load_weights_config(path: Path | str | None = None) -> WeightsConfig:
    raw = _read_yaml(Path(path) if path else _default_config_name("weights.yaml"))
    return WeightsConfig.model_validate(raw)


def load_metrics_config(path: Path | str | None = None) -> MetricsConfig:
    raw = _read_yaml(Path(path) if path else _default_config_name("metrics.yaml"))
    return MetricsConfig.model_validate(raw)


def load_patterns_config(path: Path | str | None = None) -> PatternsConfig:
    raw = _read_yaml(Path(path) if path else _default_config_name("patterns.yaml"))
    return PatternsConfig.model_validate(raw)


def validate_cross_references(
    weights_cfg: WeightsConfig, metrics_cfg: MetricsConfig, patterns_cfg: PatternsConfig
) -> list[str]:
    errors: list[str] = []

    # Metrics referenced by a dimension must exist in metrics config
    for dimension_name, weight_map in weights_cfg.dimensions.items():
        for metric_name in weight_map.keys():
            if metric_name not in metrics_cfg:
                errors.append(
                    f"Dimension '{dimension_name}' references unknown metric '{metric_name}'"
                )

    # Patterns referenced by metrics must exist in patterns config
    for metric in metrics_cfg:
        group = metric.extraction.pattern_group
        if group is not None and group not in patterns_cfg:
            errors.append(
                f"Metric '{metric.name}' references unknown pattern group '{group}'"
            )

    return errors


def load_config(
    weights_path: Path | str | None = None,
    metrics_path: Path | str | None = None,
    patterns_path: Path | str | None = None,
    *,
    strict: bool = True,
) -> tuple[WeightsConfig, MetricsConfig, PatternsConfig]:
    weights_cfg = load_weights_config(weights_path)
    metrics_cfg = load_metrics_config(metrics_path)
    patterns_cfg = load_patterns_config(patterns_path)

    if strict:
        errors = validate_cross_references(weights_cfg, metrics_cfg, patterns_cfg)
        if errors:
            raise ConfigError("Configuration validation failed:\n" + "\n".join(errors))

    return weights_cfg, metrics_cfg, patterns_cfg
