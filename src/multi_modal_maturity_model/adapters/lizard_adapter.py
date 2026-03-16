"""
Adapter for transforming Lizard collector data into core models.
"""

import logging
from typing import Any

from multi_modal_maturity_model.core.models import CodeQualityMetrics

logger = logging.getLogger(__name__)


class LizardAdapter:
    """
    Transform raw Lizard analysis data into CodeQualityMetrics domain model.
    """

    @staticmethod
    def to_code_quality_metrics(raw_data: dict[str, Any]) -> CodeQualityMetrics:
        """
        Convert raw Lizard data to CodeQualityMetrics model.

        Parameters
        ----------
        raw_data : dict[str, Any]
            Raw data dictionary from LizardCollector.fetch()

        Returns
        -------
        CodeQualityMetrics
            Structured code quality metrics model.
        """
        return CodeQualityMetrics(
            total_nloc=raw_data.get("total_nloc"),
            total_ccn=raw_data.get("total_ccn"),
            avg_ccn=raw_data.get("avg_ccn"),
            duplicate_rate=raw_data.get("duplicate_rate"),
        )
