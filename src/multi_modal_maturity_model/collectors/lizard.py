"""
Code quality metrics collection using Lizard.
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any

import lizard

logger = logging.getLogger(__name__)


class CodeQualityCollector:
    """
    Collect code quality metrics using Lizard static analysis.
    Analyzes complexity, lines of code, and duplicate code.
    """

    def __init__(self):
        """Initialize the code quality collector."""
        logger.info("CodeQualityCollector initialized")

    def collect(self, repo_url: str) -> dict[str, Any]:
        """
        Analyze code quality for a repository by cloning and running Lizard.

        Parameters
        ----------
        repo_url : str
            Git repository URL to clone and analyze

        Returns
        -------
        dict
            Dictionary with code quality metrics:
            - url: str
            - total_nloc: int | None (Sc1: total non-comment lines of code)
            - total_ccn: int | None (Su5: total cyclomatic complexity)
            - avg_ccn: float | None (Su6: average cyclomatic complexity)
            - duplicate_rate: float | None (Sc3: percentage of duplicate code)
        """
        logger.debug(f"Analyzing code quality for: {repo_url}")

        temp_dir = None
        try:
            # Create temp directory for cloning
            temp_dir = tempfile.mkdtemp(prefix="m4_lizard_")
            logger.debug(f"Created temp directory: {temp_dir}")

            self._clone_repo(repo_url, temp_dir)

            # Run lizard (python api)
            complexity_metrics = self._analyze_complexity(temp_dir)

            # Run duplicate detection (cli only)
            duplicate_rate = self._analyze_duplicates(temp_dir)

            result = {
                "url": repo_url,
                "total_nloc": complexity_metrics["total_nloc"],
                "total_ccn": complexity_metrics["total_ccn"],
                "avg_ccn": complexity_metrics["avg_ccn"],
                "duplicate_rate": duplicate_rate,
            }

            return result

        except Exception as e:
            logger.error(f"Error analyzing {repo_url}: {e}")
            return self._empty_result(repo_url)

        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temp directory: {temp_dir}")

    def _clone_repo(self, repo_url: str, target_dir: str) -> None:
        """
        Clone a git repository.

        Parameters
        ----------
        repo_url : str
            Repository URL to clone
        target_dir : str
            Target directory for clone

        Raises
        ------
        subprocess.CalledProcessError
            If git clone fails
        """
        logger.debug(f"Cloning {repo_url} to {target_dir}")

        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", "--filter=blob:none", repo_url, target_dir],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode,
                result.args,
                result.stdout,
                result.stderr
            )

    def _analyze_complexity(self, repo_path: str) -> dict[str, int | float | None]:
        """
        Analyze code complexity using Lizard.

        Parameters
        ----------
        repo_path : str
            Path to repository to analyze

        Returns
        -------
        dict
            Complexity metrics: total_nloc, total_ccn, avg_ccn
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

            avg_ccn = round(total_ccn / function_count, 2) if function_count > 0 else 0.0

            logger.debug(
                f"Complexity analysis complete: "
                f"NLOC={total_nloc}, CCN={total_ccn}, avg={avg_ccn}"
            )

            return {
                "total_nloc": total_nloc,
                "total_ccn": total_ccn,
                "avg_ccn": avg_ccn,
            }

        except Exception as e:
            logger.warning(f"Complexity analysis failed: {e}")
            return {
                "total_nloc": None,
                "total_ccn": None,
                "avg_ccn": None,
            }

    def _analyze_duplicates(self, repo_path: str) -> float | None:
        """
        Analyze code duplication using Lizard CLI (extension not in Python API).

        Parameters
        ----------
        repo_path : str
            Path to repository to analyze

        Returns
        -------
        float | None
            Duplicate rate percentage, or None if analysis fails
        """
        logger.debug(f"Running duplicate analysis on {repo_path}")

        try:
            # Must use CLI for -Eduplicate extension
            result = subprocess.run(
                ["lizard", "-Eduplicate", repo_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=150
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

    def _empty_result(self, repo_url: str) -> dict[str, Any]:
        """
        Return an empty/failed result structure.

        Parameters
        ----------
        repo_url : str
            Repository URL

        Returns
        -------
        dict
            Result with all None values
        """
        return {
            "url": repo_url,
            "total_nloc": None,
            "total_ccn": None,
            "avg_ccn": None,
            "duplicate_rate": None,
        }
