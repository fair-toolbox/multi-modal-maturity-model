"""
Pydantic models mirroring the structure of the configuration files (weights.yaml, metrics.yaml, patterns.yaml).
These models validate shape and internal consistency of a single config file.
"""

from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator
from typing import Any, Literal


class WeightMap(RootModel[dict[str, float]]):

    @model_validator(mode="after")
    def _check_non_negative_and_non_empty(self) -> "WeightMap":
        if not self.root:
            raise ValueError("Weight mapping cannot be empty")
        for key, weight in self.root.items():
            if weight < 0:
                raise ValueError(f"Weight for {key} must be non-negative, got {weight}")
        return self

    def sum(self) -> float:
        return sum(self.root.values())

    def keys(self):
        return self.root.keys()

    def items(self):
        return self.root.items()


class WeightsConfig(BaseModel):
    """Configuration for weights used in the Multi-Modal Maturity Model.

    Attributes
    ----------
    dimensions : dict[str, WeightMap]
        Weights for each dimension (e.g., 'data', 'model', 'deployment')
    overall : WeightMap
        Overall weight for the model
    """

    dimensions: dict[str, WeightMap]
    overall: WeightMap

    @model_validator(mode="after")
    def _check_overall_references_known_dimensions(self) -> "WeightsConfig":
        dimension_names = set(self.dimensions.keys())
        overall_names = set(self.overall.keys())
        unknown = overall_names - dimension_names
        if unknown:
            raise ValueError(
                f"Overall weight references unknown dimensions: {', '.join(unknown)}"
            )
        return self

    def weight_sum_warnings(self, tolerance: float = 1e-6) -> list[str]:
        """
        Check if the sum of weights for each dimension and overall is 1.0.

        Non-fatal, weighted averagees only need relative weights but a large drift from 1.0 may indicate a misconfiguration.

        Returns
        -------
        list[str]
            List of warnings for dimensions or overall weights that do not sum to 1.0 within the specified tolerance.
        """
        warnings = []
        for name, weight_map in self.dimensions.items():
            total = weight_map.sum()
            if abs(total - 1.0) > tolerance:
                warnings.append(
                    f"Sum of weights for dimension '{name}' is {total:.4f}, expected 1.0"
                )
        overall_total = self.overall.sum()
        if abs(overall_total - 1.0) > tolerance:
            warnings.append(
                f"Sum of overall weights is {overall_total:.4f}, expected 1.0"
            )
        return warnings


MetricType = Literal["boolean", "numeric"]
ExtractionMethod = Literal[
    "direct", "calculated", "pattern_match", "existence_check", "publication"
]
AggregationFn = Literal["sum", "any", "mean", "max"]
Scaler = Literal["clamp", "log", "fraction"]


class SourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    params: dict[str, Any] | None = None


class ExtractionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: ExtractionMethod
    sources: dict[str, SourceConfig]
    pattern_group: str | None = None
    function: str | None = None
    aggregation: AggregationFn | None = None

    @model_validator(mode="after")
    def _check_method_specific_fields(self) -> "ExtractionConfig":
        if not self.sources:
            raise ValueError("extraction.sources must not be empty")

        required_field_by_method: dict[str, tuple[str, Any]] = {
            "pattern_match": ("pattern_group", self.pattern_group),
            "calculated": ("function", self.function),
            "publication": ("aggregation", self.aggregation),
        }
        if self.method in required_field_by_method:
            field_name, value = required_field_by_method[self.method]
            if value is None:
                raise ValueError(
                    f"extraction.{field_name} is required when method='{self.method}'"
                )
        return self


class NormalizationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scaler: Scaler
    lo: float | None = None
    hi: float | None = None
    invert: bool = False
    cap: float | None = None

    @model_validator(mode="after")
    def _check_scaler_specific_fields(self) -> "NormalizationConfig":
        if self.scaler in ("clamp", "fraction"):
            if self.lo is None or self.hi is None:
                raise ValueError(
                    f"normalization.lo and normalization.hi are required when scaler='{self.scaler}'"
                )
            if self.hi <= self.lo:
                raise ValueError(
                    f"normalization.hi ({self.hi}) must be greater than normalization.lo ({self.lo})"
                )
        if self.scaler == "log":
            if self.cap is None:
                raise ValueError("normalization.cap is required when scaler='log'")
            if self.cap <= 0:
                raise ValueError(
                    f"normalization.cap ({self.cap}) must be greater than 0"
                )
        return self


class MetricSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(exclude=True)
    type: MetricType
    description: str
    extraction: ExtractionConfig
    normalization: NormalizationConfig | None = None

    @model_validator(mode="after")
    def _check_normalization_matches_type(self) -> "MetricSpec":
        if self.type == "numeric" and self.normalization is None:
            raise ValueError(f"metric '{self.name}' requires a normalization block")
        if self.type == "boolean" and self.normalization is not None:
            raise ValueError(
                f"boolean metric '{self.name}' should not have a normalization block"
            )
        return self


class MetricsConfig(BaseModel):

    model_config = ConfigDict(extra="ignore")

    metrics: dict[str, MetricSpec]

    @model_validator(mode="before")
    @classmethod
    def _inject_names(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("metrics"), dict):
            data = dict(data)
            data["metrics"] = {
                name: {**body, "name": name} for name, body in data["metrics"].items()
            }
        return data

    def __getitem__(self, name: str) -> MetricSpec:
        return self.metrics[name]

    def __contains__(self, name: str) -> bool:
        return name in self.metrics

    def __iter__(self):
        return iter(self.metrics.values())

    def __len__(self) -> int:
        return len(self.metrics)


class PatternsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pattern_groups: dict[str, list[str]]

    def __getitem__(self, group: str) -> list[str]:
        return self.pattern_groups[group]

    def __contains__(self, group: str) -> bool:
        return group in self.pattern_groups
