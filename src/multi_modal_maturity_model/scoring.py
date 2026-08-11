from .config import WeightsConfig
from .models import DimensionScore


class DimensionScorer:
    def __init__(self, weights_cfg: WeightsConfig):
        self.dimensions = weights_cfg.dimensions

    def score(self, normalized: dict[str, float | None]) -> dict[str, DimensionScore]:
        out = {}
        for dim, metric_weights in self.dimensions.items():
            available = {
                m: (normalized.get(m), w)
                for m, w in metric_weights.items()
                if normalized.get(m) is not None
            }
            if not available:
                out[dim] = DimensionScore(dim, None, 0.0, [])
                continue
            weight_sum = sum(w for _, w in available.values())
            score = sum(v * w for v, w in available.values()) / weight_sum
            out[dim] = DimensionScore(
                dim, score, len(available) / len(metric_weights), list(available)
            )
        return out


class OverallScorer:
    def __init__(self, weights_cfg: WeightsConfig):
        self.overall_weights = weights_cfg.overall

    def aggregate(self, dims: dict[str, DimensionScore]) -> float | None:
        available = {
            d: (ds.score, self.overall_weights[d])
            for d, ds in dims.items()
            if ds.score is not None
        }
        if not available:
            return None
        weight_sum = sum(w for _, w in available.values())
        return sum(s * w for s, w in available.values()) / weight_sum
