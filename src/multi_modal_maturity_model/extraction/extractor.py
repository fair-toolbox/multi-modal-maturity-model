import logging
from typing import Any

from .methods import EXTRACTION_METHODS
from ..config import ExtractionConfig, MetricsConfig, PatternsConfig, SourceConfig

logger = logging.getLogger(__name__)


class MetricExtractor:
    def __init__(self, metrics_cfg: MetricsConfig, patterns_cfg: PatternsConfig):
        self.metrics_cfg = metrics_cfg
        self.patterns_cfg = patterns_cfg

    def extract_all(self, results: dict[str, Any]) -> dict[str, Any]:
        extracted = {}

        for m in self.metrics_cfg:
            extracted[m.name] = self._extract_one(m.name, m.extraction, results)

        return extracted

    def _extract_one(
        self, metric_name: str, cfg: ExtractionConfig, raw_data: dict[str, Any]
    ) -> Any | None:

        method = EXTRACTION_METHODS[cfg.method]

        for source_name, source_cfg in cfg.sources.items():
            if source_name not in raw_data:
                continue

            try:
                value = method(
                    raw_data[source_name],
                    path=source_cfg.path,
                    **self._extra_kwargs(cfg, source_cfg),
                )
            except Exception as e:
                logger.warning(
                    f"Error extracting '{metric_name}' from '{source_name}': {e}"
                )
                continue

            if value is not None:
                return value

        return None

    def _extra_kwargs(
        self, extraction: ExtractionConfig, source: SourceConfig
    ) -> dict[str, Any]:
        kwargs = {}

        if extraction.method == "pattern_match":
            kwargs["pattern_group"] = extraction.pattern_group
            kwargs["patterns_cfg"] = self.patterns_cfg

        elif extraction.method == "calculated":
            kwargs["fn_name"] = extraction.function
            kwargs["params"] = source.params

        elif extraction.method == "publication":
            kwargs["aggregation"] = extraction.aggregation

        return kwargs
