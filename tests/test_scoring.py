"""Tests for dimension and overall scoring."""

from multi_modal_maturity_model.config import WeightsConfig, load_config
from multi_modal_maturity_model.scoring import _weighted_average, score_all


class TestWeightedAverage:
    def test_all_values_present(self):
        score, weights = _weighted_average({"a": 1.0, "b": 0.0}, {"a": 0.5, "b": 0.5})
        assert score == 0.5
        assert weights == {"a": 0.5, "b": 0.5}

    def test_some_values_missing_renormalizes_weights(self):
        score, weights = _weighted_average({"a": 1.0, "b": None}, {"a": 0.3, "b": 0.7})
        assert score == 1.0
        assert weights == {"a": 1.0, "b": 0.0}

    def test_no_values_available(self):
        score, weights = _weighted_average({"a": None, "b": None}, {"a": 0.5, "b": 0.5})
        assert score is None
        assert weights == {"a": 0.0, "b": 0.0}


def _weights_cfg(dimensions: dict, overall: dict) -> WeightsConfig:
    return WeightsConfig.model_validate({"dimensions": dimensions, "overall": overall})


class TestScoreAll:
    def test_dimension_with_all_metrics_available(self):
        weights_cfg = _weights_cfg(
            dimensions={"quality": {"m1": 0.5, "m2": 0.5}}, overall={"quality": 1.0}
        )
        result = score_all(
            extracted_metrics={"m1": 10, "m2": 20},
            normalized_metrics={"m1": 1.0, "m2": 0.0},
            weights_cfg=weights_cfg,
        )

        dimension = result.dimensions[0]
        assert dimension.dimension == "quality"
        assert dimension.score == 0.5
        assert {m.metric: m.weight for m in dimension.metrics} == {"m1": 0.5, "m2": 0.5}
        assert result.overall_score == 0.5

    def test_dimension_with_missing_metric_renormalizes_and_keeps_raw_value(self):
        weights_cfg = _weights_cfg(
            dimensions={"quality": {"m1": 0.5, "m2": 0.5}}, overall={"quality": 1.0}
        )
        result = score_all(
            extracted_metrics={"m1": 10, "m2": None},
            normalized_metrics={"m1": 1.0, "m2": None},
            weights_cfg=weights_cfg,
        )

        dimension = result.dimensions[0]
        by_metric = {m.metric: m for m in dimension.metrics}
        assert dimension.score == 1.0
        assert by_metric["m1"].weight == 1.0
        assert by_metric["m1"].contribution == 1.0
        assert by_metric["m2"].weight == 0.0
        assert by_metric["m2"].contribution == 0.0
        assert by_metric["m2"].normalized_value is None
        assert by_metric["m2"].raw_value is None

    def test_dimension_with_no_available_metrics_has_none_score(self):
        weights_cfg = _weights_cfg(
            dimensions={"quality": {"m1": 1.0}}, overall={"quality": 1.0}
        )
        result = score_all(
            extracted_metrics={}, normalized_metrics={}, weights_cfg=weights_cfg
        )

        dimension = result.dimensions[0]
        assert dimension.score is None
        assert dimension.metrics[0].weight == 0.0
        assert dimension.metrics[0].contribution == 0.0
        assert result.overall_score is None

    def test_overall_score_renormalizes_across_missing_dimensions(self):
        weights_cfg = _weights_cfg(
            dimensions={
                "quality": {"m1": 1.0},
                "security": {"m2": 1.0},
            },
            overall={"quality": 0.5, "security": 0.5},
        )
        result = score_all(
            extracted_metrics={"m1": 10},
            normalized_metrics={"m1": 1.0, "m2": None},
            weights_cfg=weights_cfg,
        )

        assert result.overall_score == 1.0


class TestScoreAllWithDefaultConfig:
    def test_runs_end_to_end_with_real_config(self):
        weights_cfg, metrics_cfg, _ = load_config()

        normalized_metrics = {m.name: None for m in metrics_cfg}
        normalized_metrics["star_count"] = 0.5
        normalized_metrics["license"] = 1.0

        extracted_metrics = {"star_count": 50, "license": True}

        result = score_all(extracted_metrics, normalized_metrics, weights_cfg)

        assert result.overall_score is not None
        assert any(d.dimension == "fairness" for d in result.dimensions)
