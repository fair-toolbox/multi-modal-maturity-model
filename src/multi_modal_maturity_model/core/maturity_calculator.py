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

    def analyze_repositories(
        self,
        repo_urls: list[str],
        pmids: list[str] | None = None,
        output_dir: str | Path = "./data/results",
    ) -> dict[str, Any]:
        """
        Collect all metrics for a list of repositories (main entry point for batch analysis).

        Parameters
        ----------
        repo_urls : list[str]
            List of GitHub/GitLab repository URLs
        pmids : list[str], optional
            List of PMIDs corresponding to each repository.
        output_dir : str or Path, optional
            Directory to save results (default: "./data/results")

        Returns
        -------
        dict
            Dictionary with metrics:
            - 'github': list of GitHub metrics
            - 'fairness': list of FAIR compliance metrics
            - 'code_quality': list of code quality metrics
            - 'citations': list of citation metrics
        """

        logger.info(f"Starting analysis of {len(repo_urls)} repositories")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}

        logger.info("Collecting GitHub metrics...")
        results['github'] = self._collect_github_metrics(repo_urls)
        self._save_to_csv(results['github'], output_dir / "github_metrics.csv")

        logger.info("Collecting FAIRness metrics...")
        results['fairness'] = self._collect_fairness_metrics(repo_urls)
        self._save_to_csv(results['fairness'], output_dir / "fairness_metrics.csv")

        logger.info("Collecting code quality metrics...")
        results['code_quality'] = self._collect_code_quality_metrics(repo_urls)
        self._save_to_csv(results['code_quality'], output_dir / "code_quality_metrics.csv")

        if pmids:
            logger.info("Collecting citation metrics...")
            results['citations'] = self._collect_citation_metrics(pmids)
            self._save_to_csv(results['citations'], output_dir / "citation_metrics.csv")
        else:
            logger.info("Skipping citation collection (no PMIDs provided)")
            results['citations'] = []

        logger.info(f"Analysis complete. Results saved to {output_dir}")
        return results
