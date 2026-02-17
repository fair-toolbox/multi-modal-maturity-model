# src/multi_modal_maturity_model/core/maturity_calculator.py

"""
Main orchestrator for maturity model calculations.
Coordinates all data collectors and exporters.
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from ..collectors import (
    GitHubMetricsCollector,
    EuropePMCCollector,
    FairnessCollector,
    CodeQualityCollector,
)

logger = logging.getLogger(__name__)


class MaturityCalculator:
    """
    Main orchestrator for collecting maturity metrics.
    """

    def __init__(
        self,
        github_token: str,
        rate_limit_seconds: int = 60,
    ):
        """
        Initialize the maturity calculator with all collectors.

        Parameters
        ----------
        github_token : str
            GitHub personal access token for API access
        rate_limit_seconds : int, optional
            Seconds to wait between rate-limited API calls (default: 60)

        Examples
        --------
        >>> calc = MaturityCalculator(github_token="ghp_xxx")
        >>> results = calc.analyze_repositories(["https://github.com/owner/repo"])
        """
        logger.info("Initializing MaturityCalculator")

        # Initialize collectors
        self.github = GitHubMetricsCollector(token=github_token)
        self.citations = EuropePMCCollector()
        self.fairness = FairnessCollector(rate_limit_seconds=rate_limit_seconds)
        self.code_quality = CodeQualityCollector()

        logger.info("All collectors initialized successfully")
