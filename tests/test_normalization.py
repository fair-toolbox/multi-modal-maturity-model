"""Tests for metric normalization."""

import pytest
from multi_modal_maturity_model.normalization import (
    normalize_metric,
    normalize_metrics,
)


class TestNormalizeMetric:
    """Test single metric normalization."""

    def test_clamp_normalization(self):
        sources = {"github": 50}
        config = {
            "normalization": {
                "scaler": "clamp",
                "lo": 0.0,
                "hi": 100.0,
                "invert": False,
            }
        }
        result = normalize_metric("star_count", sources, config)
        assert result == 0.5

    def test_clamp_with_invert(self):
        sources = {"github": 100}
        config = {
            "normalization": {"scaler": "clamp", "lo": 0.0, "hi": 200.0, "invert": True}
        }
        result = normalize_metric("num_open_issues", sources, config)
        assert result == 0.5

    def test_log_normalization(self):
        sources = {"openalex": 100}
        config = {"normalization": {"scaler": "log", "cap": 100.0}}
        result = normalize_metric("citation_count", sources, config)
        assert result == 1.0

    def test_fraction_normalization(self):
        sources = {"biotools": 0.75}
        config = {"normalization": {"scaler": "fraction", "lo": 0.0, "hi": 1.0}}
        result = normalize_metric("input_formats", sources, config)
        assert result == 0.75

    def test_boolean_value_with_clamp(self):
        sources = {"howfairis": True}
        config = {
            "normalization": {"scaler": "clamp", "lo": 0.0, "hi": 1.0, "invert": False}
        }
        result = normalize_metric("license", sources, config)
        assert result == 1.0

    def test_boolean_value_without_config(self):
        sources = {"howfairis": True}
        config = {}  # No normalization config
        result = normalize_metric("license", sources, config)
        assert result == 1.0

    def test_missing_value_returns_none(self):
        sources = {}
        config = {"normalization": {"scaler": "clamp", "lo": 0.0, "hi": 100.0}}
        result = normalize_metric("star_count", sources, config)
        assert result is None

    def test_none_value_returns_none(self):
        sources = {"github": None}
        config = {"normalization": {"scaler": "clamp", "lo": 0.0, "hi": 100.0}}
        result = normalize_metric("star_count", sources, config)
        assert result is None

    def test_no_normalization_config_passes_through_numeric(self):
        sources = {"github": 42}
        config = {}  # No normalization section
        result = normalize_metric("star_count", sources, config)
        assert result == 42

    def test_unknown_scaler_logs_warning(self, caplog):
        sources = {"github": 50}
        config = {"normalization": {"scaler": "unknown_scaler"}}
        result = normalize_metric("star_count", sources, config)
        assert result == 50  # Falls back to raw value
        assert "Unknown scaler type" in caplog.text


class TestNormalizeMetrics:
    """Test batch normalization of all metrics."""

    def test_normalize_multiple_metrics(self):
        extracted = {
            "star_count": {"github": 50},
            "license": {"howfairis": True},
            "fwci": {"openalex": 1.0},
        }

        metrics_cfg = {
            "star_count": {
                "normalization": {"scaler": "clamp", "lo": 0.0, "hi": 100.0}
            },
            "license": {"normalization": {"scaler": "fraction"}},
            "fwci": {"normalization": {"scaler": "clamp", "lo": 0.0, "hi": 2.0}},
        }

        result = normalize_metrics(extracted, metrics_cfg)

        assert result["star_count"] == 0.5
        assert result["license"] == 1.0
        assert result["fwci"] == 0.5

    def test_exclude_none_values(self):
        extracted = {
            "star_count": {"github": 50},
            "fork_count": {"github": None},  # None value
            "citation_count": {},  # Empty sources
        }

        metrics_cfg = {
            "star_count": {
                "normalization": {"scaler": "clamp", "lo": 0.0, "hi": 100.0}
            },
            "fork_count": {
                "normalization": {"scaler": "clamp", "lo": 0.0, "hi": 100.0}
            },
            "citation_count": {"normalization": {"scaler": "log", "cap": 200.0}},
        }

        result = normalize_metrics(extracted, metrics_cfg)

        assert "star_count" in result
        assert result["star_count"] == 0.5
        assert "fork_count" not in result  # Excluded because value is None
        assert "citation_count" not in result  # Excluded because no value

    def test_mixed_scalers(self):
        extracted = {
            "star_count": {"github": 100},
            "citation_count": {"openalex": 50},
            "input_formats": {"biotools": 0.8},
            "license": {"howfairis": False},
        }

        metrics_cfg = {
            "star_count": {
                "normalization": {"scaler": "clamp", "lo": 0.0, "hi": 100.0}
            },
            "citation_count": {"normalization": {"scaler": "log", "cap": 200.0}},
            "input_formats": {"normalization": {"scaler": "fraction"}},
            "license": {"normalization": {"scaler": "fraction"}},
        }

        result = normalize_metrics(extracted, metrics_cfg)

        assert result["star_count"] == 1.0
        assert 0.0 < result["citation_count"] < 1.0
        assert result["input_formats"] == 0.8
        assert result["license"] == 0.0

    def test_invert_flag_integration(self):
        extracted = {
            "num_open_issues": {"github": 0},  # 0 issues is good
            "days_since_last_commit": {"github": 180},  # 180 days is bad
        }

        metrics_cfg = {
            "num_open_issues": {
                "normalization": {
                    "scaler": "clamp",
                    "lo": 0.0,
                    "hi": 200.0,
                    "invert": True,
                }
            },
            "days_since_last_commit": {
                "normalization": {
                    "scaler": "clamp",
                    "lo": 0.0,
                    "hi": 180.0,
                    "invert": True,
                }
            },
        }

        result = normalize_metrics(extracted, metrics_cfg)

        assert result["num_open_issues"] == 1.0  # 0 issues = perfect
        assert result["days_since_last_commit"] == 0.0  # 180 days = worst

    def test_empty_input(self):
        result = normalize_metrics({}, {})
        assert result == {}

    def test_metric_without_config(self):
        extracted = {"unknown_metric": {"github": 42}}
        metrics_cfg = {}

        result = normalize_metrics(extracted, metrics_cfg)

        # Should pass through raw value
        assert result["unknown_metric"] == 42

    def test_realistic_example(self):
        """Test with realistic metric values from the codebase."""
        extracted = {
            "input_formats": {"biotools": 1.0},
            "biotools_registry": {"biotools": True},
            "default_branch_protected": {"github": True},
            "star_count": {"github": 100},
            "fork_count": {"github": 50},
            "num_open_issues": {"github": 0},
            "has_workflow_support": {"github": False},
            "has_distribution_support": {"github": False},
            "has_security_policy": {"github": False},
            "has_security_scanning": {"github": False},
            "days_since_last_commit": {"github": 0},
            "avg_issue_close_time_days": {"github": 0.0},
            "inverse_simpson_index": {"github": 8.26},
            "publication_open_access": {"openalex": False},
            "fwci": {"openalex": 2.0},
            "citation_count": {"openalex": 200},
        }

        metrics_cfg = {
            "input_formats": {"normalization": {"scaler": "fraction"}},
            "star_count": {
                "normalization": {"scaler": "clamp", "lo": 0.0, "hi": 100.0}
            },
            "fork_count": {
                "normalization": {"scaler": "clamp", "lo": 0.0, "hi": 100.0}
            },
            "num_open_issues": {
                "normalization": {
                    "scaler": "clamp",
                    "lo": 0.0,
                    "hi": 200.0,
                    "invert": True,
                }
            },
            "days_since_last_commit": {
                "normalization": {
                    "scaler": "clamp",
                    "lo": 0.0,
                    "hi": 180.0,
                    "invert": True,
                }
            },
            "avg_issue_close_time_days": {
                "normalization": {
                    "scaler": "clamp",
                    "lo": 0.0,
                    "hi": 90.0,
                    "invert": True,
                }
            },
            "inverse_simpson_index": {
                "normalization": {"scaler": "clamp", "lo": 1.0, "hi": 20.0}
            },
            "fwci": {"normalization": {"scaler": "clamp", "lo": 0.0, "hi": 2.0}},
            "citation_count": {"normalization": {"scaler": "log", "cap": 200.0}},
        }

        result = normalize_metrics(extracted, metrics_cfg)

        # Verify expected outputs
        assert result["input_formats"] == 1.0
        assert result["biotools_registry"] == 1.0  # True → 1.0
        assert result["default_branch_protected"] == 1.0
        assert result["star_count"] == 1.0  # 100/100
        assert result["fork_count"] == 0.5  # 50/100
        assert result["num_open_issues"] == 1.0  # 0 issues inverted = perfect
        assert result["has_workflow_support"] == 0.0
        assert result["days_since_last_commit"] == 1.0  # 0 days inverted = perfect
        assert result["avg_issue_close_time_days"] == 1.0  # 0 days inverted = perfect
        assert result["fwci"] == 1.0  # 2.0/2.0
        assert result["citation_count"] == 1.0  # log(201)/log(201)
