"""
Code quality metrics collection using Lizard.
"""

import logging
import re
import subprocess
from typing import Any

import lizard

logger = logging.getLogger(__name__)


class LizardAnalyzer:
    """
    Collect code quality metrics using Lizard static analysis.
    Analyzes complexity, lines of code, and duplicate code.
    """

    def __init__(self):
        """Initialize the lizard client."""

    def analyze(self, repo_path: str) -> dict[str, Any]:
        """
        Analyze code quality for a repository.

        Parameters
        ----------
        repo_path : str
            Path to local repository to analyze

        Returns
        -------
        dict[str, Any]
            Dictionary with code quality metrics:
            - path: str
            - total_nloc: int | None
            - total_ccn: int | None
            - avg_ccn: float | None
            - duplicate_rate: float | None
        """
        logger.debug(f"Analyzing code quality for: {repo_path}")

        complexity_metrics = self._analyze_complexity(repo_path)
        duplicate_rate = self._analyze_duplicates(repo_path)

        result = {
            "total_nloc": complexity_metrics["total_nloc"],
            "total_ccn": complexity_metrics["total_ccn"],
            "avg_ccn": complexity_metrics["avg_ccn"],
            "duplicate_rate": duplicate_rate,
        }

        logger.info(f"Successfully collected code quality metrics for {repo_path}")
        return result

    def _analyze_complexity(self, repo_path: str) -> dict[str, int | float] | None:
        """
        Analyze code complexity using Lizard API.
        """
        logger.debug(f"Running Lizard complexity analysis on {repo_path}")

        try:
            results = lizard.analyze([repo_path])

            total_nloc = 0
            total_ccn = 0
            function_count = 0

            for file_result in results:
                for func in file_result.function_list:
                    total_nloc += func.nloc
                    total_ccn += func.cyclomatic_complexity
                    function_count += 1

            avg_ccn = (
                round(total_ccn / function_count, 2) if function_count > 0 else 0.0
            )

            logger.debug(f"Complexity analysis complete.")

            return {
                "total_nloc": total_nloc,
                "total_ccn": total_ccn,
                "avg_ccn": avg_ccn,
            }

        except Exception as e:
            logger.warning(f"Complexity analysis failed: {e}")
            return None

    def _analyze_duplicates(self, repo_path: str) -> float | None:
        """
        Analyze code duplication using Lizard CLI extension.
        """
        logger.debug(f"Running duplicate analysis on {repo_path}")

        try:
            # Must use CLI for -Eduplicate extension
            result = subprocess.run(
                ["lizard", "-Eduplicate", repo_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=150,
            )

            # Parse output for duplicate rate
            match = re.search(r"Total duplicate rate:\s+([\d.]+)%", result.stdout)

            if match:
                duplicate_rate = float(match.group(1))
                logger.debug(f"Duplicate rate: {duplicate_rate}%")
                return duplicate_rate
            else:
                logger.warning("Could not find duplicate rate in output")
                return None

        except Exception as e:
            logger.warning(f"Duplicate analysis failed: {e}")
            return None
