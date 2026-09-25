"""Tests for metric normalization."""

import pytest

from mmmm.config import (
    ExtractionConfig,
    MetricsConfig,
    MetricSpec,
    NormalizationConfig,
    load_config,
)
from mmmm.normalization import (
    normalize_metric,
    normalize_all,
)

_, metrics_cfg, _ = load_config(weights_path=None)


def make_spec(
    normalization: dict | None = None,
    *,
    name: str = "test_metric",
    metric_type: str | None = None,
) -> MetricSpec:
    """Build a valid MetricSpec, inferring type from presence of normalization."""
    if metric_type is None:
        metric_type = "numeric" if normalization is not None else "boolean"

    data: dict = {
        "name": name,
        "type": metric_type,
        "description": "metric used in tests",
        "extraction": {
            "method": "direct",
            "sources": {"github": {"path": "value"}},
        },
    }
    if normalization is not None:
        data["normalization"] = normalization

    return MetricSpec.model_validate(data)


class TestNormalizeMetric:
    """Test single metric normalization."""

    def test_clamp_normalization(self):
        spec = make_spec({"scaler": "clamp", "lo": 0.0, "hi": 100.0, "invert": False})
        result = normalize_metric("star_count", 50, spec)
        assert result == 0.5

    def test_clamp_with_invert(self):
        spec = make_spec({"scaler": "clamp", "lo": 0.0, "hi": 200.0, "invert": True})
        result = normalize_metric("num_open_issues", 100, spec)
        assert result == 0.5

    def test_log_normalization(self):
        spec = make_spec({"scaler": "log", "cap": 100.0})
        result = normalize_metric("citation_count", 100, spec)
        assert result == 1.0

    def test_fraction_normalization(self):
        spec = make_spec({"scaler": "fraction", "lo": 0.0, "hi": 1.0})
        result = normalize_metric("input_formats", 0.75, spec)
        assert result == 0.75

    def test_boolean_value_with_clamp(self):
        # Booleans are normalized to 0.0/1.0 before the scaler config is
        # applied. A boolean metric with a normalization block is not
        # schema-valid, so construct the spec without validation.
        spec = MetricSpec.model_construct(
            name="license",
            type="boolean",
            description="",
            extraction=ExtractionConfig.model_validate(
                {"method": "direct", "sources": {"howfairis": {"path": "license"}}}
            ),
            normalization=NormalizationConfig.model_validate(
                {"scaler": "clamp", "lo": 0.0, "hi": 1.0, "invert": False}
            ),
        )
        result = normalize_metric("license", True, spec)
        assert result == 1.0

    def test_boolean_value_without_config(self):
        spec = make_spec()  # No normalization config
        result = normalize_metric("license", True, spec)
        assert result == 1.0

    def test_missing_value_returns_none(self):
        spec = make_spec({"scaler": "clamp", "lo": 0.0, "hi": 100.0})
        result = normalize_metric("star_count", None, spec)
        assert result is None

    def test_none_value_returns_none(self):
        spec = make_spec({"scaler": "clamp", "lo": 0.0, "hi": 100.0})
        result = normalize_metric("star_count", None, spec)
        assert result is None

    def test_no_normalization_config_passes_through_numeric(self):
        spec = make_spec()  # No normalization section
        result = normalize_metric("star_count", 42, spec)
        assert result == 42


class TestNormalizeMetrics:
    """Test batch normalization of all metrics."""

    def test_normalize_multiple_metrics(self):
        extracted = {
            "star_count": 50,
            "license": True,
            "fwci": 1.0,
        }

        result = normalize_all(extracted, metrics_cfg)

        assert result["star_count"] == 0.5
        assert result["license"] == 1.0
        assert result["fwci"] == 0.5

    def test_include_none_values(self):
        extracted = {
            "star_count": 50,
            "fork_count": None,  # None value
            "citation_count": None,  # No value
        }

        result = normalize_all(extracted, metrics_cfg)

        assert "star_count" in result
        assert result["star_count"] == 0.5
        assert "fork_count" in result  # Included because value is None
        assert result["fork_count"] is None
        assert "citation_count" in result  # Included because no value
        assert result["citation_count"] is None

    def test_invert_flag_integration(self):
        extracted = {
            "num_open_issues": 0,  # 0 issues is good
            "days_since_last_commit": 180,  # 180 days is bad
        }

        result = normalize_all(extracted, metrics_cfg)

        assert result["num_open_issues"] == 1.0  # 0 issues = perfect
        assert result["days_since_last_commit"] == 0.0  # 180 days = worst

    def test_empty_input(self):
        empty_cfg = MetricsConfig.model_validate({"metrics": {}})
        result = normalize_all({}, empty_cfg)
        assert result == {}

    def test_realistic_example(self):
        """Test with realistic metric values from the codebase."""
        extracted = {
            "input_formats": 1.0,
            "biotools_registry": True,
            "default_branch_protected": True,
            "star_count": 100,
            "fork_count": 50,
            "num_open_issues": 0,
            "has_workflow_support": False,
            "has_distribution_support": False,
            "has_security_policy": False,
            "secret_scanning": False,
            "days_since_last_commit": 0,
            "avg_issue_close_time_days": 0.0,
            "inverse_simpson_index": 8.26,
            "publication_open_access": False,
            "fwci": 2.0,
            "citation_count": 200,
        }

        result = normalize_all(extracted, metrics_cfg)

        # Verify expected outputs
        assert result["input_formats"] == 1.0
        assert result["biotools_registry"] == 1.0  # True → 1.0
        assert result["default_branch_protected"] == 1.0
        assert result["star_count"] == 1.0  # 100/100
        assert result["fork_count"] == 0.5  # 50/100
        assert result["num_open_issues"] == 1.0  # 0 issues inverted = perfect
        assert result["has_workflow_support"] == 0.0
        assert result["secret_scanning"] == 0.0
        assert result["days_since_last_commit"] == 1.0  # 0 days inverted = perfect
        assert result["avg_issue_close_time_days"] == 1.0  # 0 days inverted = perfect
        assert result["fwci"] == 1.0  # 2.0/2.0
        assert result["citation_count"] == 1.0  # log1p(200)/log1p(200)
