"""Code quality metrics collection using Lizard."""

import lizard
import logging
import re
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


class LizardAnalyzer:
    """
    Collect code quality metrics using Lizard static analysis.

    Parameters
    ----------
    repo_path : str
        Path to the local repository to analyze.
    """

    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def analyze(self) -> dict[str, Any] | None:
        """
        Analyze code quality for a repository.

        Returns
        -------
        dict[str, Any] | None
            Dictionary with code quality metrics
        """
        logger.debug(f"Analyzing code quality for: {self.repo_path}")

        complexity_metrics = self._analyze_complexity()

        if complexity_metrics is None:
            return None

        duplicate_rate = self._analyze_duplicates()

        result = {
            "total_nloc": complexity_metrics["total_nloc"],
            "total_ccn": complexity_metrics["total_ccn"],
            "avg_ccn": complexity_metrics["avg_ccn"],
            "nloc_per_file": complexity_metrics["nloc_per_file"],
            "duplicate_rate": duplicate_rate,
        }

        return result

    def _analyze_complexity(self) -> dict[str, int | float] | None:
        """
        Analyze code complexity using Lizard API.
        """
        logger.debug(f"Running Lizard complexity analysis on {self.repo_path}")

        try:
            results = lizard.analyze([self.repo_path])

            total_nloc = 0
            total_ccn = 0
            function_count = 0
            file_count = 0

            for file_result in results:
                file_count += 1
                for func in file_result.function_list:
                    total_nloc += func.nloc
                    total_ccn += func.cyclomatic_complexity
                    function_count += 1

            nloc_per_file = round(total_nloc / file_count, 2) if file_count > 0 else 0.0

            avg_ccn = (
                round(total_ccn / function_count, 2) if function_count > 0 else 0.0
            )

            return {
                "total_nloc": total_nloc,
                "total_ccn": total_ccn,
                "avg_ccn": avg_ccn,
                "nloc_per_file": nloc_per_file,
            }

        except Exception as e:
            logger.error(f"Complexity analysis failed: {e}")
            return None

    def _analyze_duplicates(self) -> float | None:
        """
        Analyze code duplication using Lizard CLI extension.
        """
        logger.debug(f"Running duplicate analysis on {self.repo_path}")

        try:
            # Must use CLI for -Eduplicate extension
            result = subprocess.run(
                ["lizard", "-Eduplicate", self.repo_path],
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
            logger.error(f"Duplicate analysis failed: {e}")
            return None
