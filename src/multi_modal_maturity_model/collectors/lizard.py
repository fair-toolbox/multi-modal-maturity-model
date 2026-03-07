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
        Analyze code quality for a repository.

        Accepts either a Git repository URL (will be cloned) or a local path
        to an existing repository.

        Parameters
        ----------
        repo_url : str
            Git repository URL to clone and analyze, or local path to existing repository

        Returns
        -------
        dict
            Dictionary with code quality metrics:
            - url: str
            - total_nloc: int | None (Sc1: total non-comment lines of code)
            - total_ccn: int | None (Su5: total cyclomatic complexity)
            - avg_ccn: float | None (Su6: average cyclomatic complexity)
            - duplicate_rate: float | None (Sc3: percentage of duplicate code)

        Raises
        ------
        subprocess.CalledProcessError
            If git clone fails (for remote URLs)
        FileNotFoundError
            If local path does not exist
        Exception
            For other unexpected failures during clone/setup

        Note
        ----
        Analysis failures (lizard execution) return None values rather than raising.
        Only repository access failures (clone, invalid path) raise exceptions.
        """
        logger.debug(f"Analyzing code quality for: {repo_url}")

        temp_dir = None
        should_cleanup = False

        try:
            # Determine if input is a local path or URL
            if self._is_local_path(repo_url):
                logger.debug(f"Using existing local repository: {repo_url}")
                analysis_path = repo_url
            else:
                # Create temp directory for cloning
                temp_dir = tempfile.mkdtemp(prefix="m4_lizard_")
                logger.debug(f"Created temp directory: {temp_dir}")
                should_cleanup = True

                self._clone_repo(repo_url, temp_dir)
                analysis_path = temp_dir

            # Run lizard (python api)
            complexity_metrics = self._analyze_complexity(analysis_path)

            # Run duplicate detection (cli only)
            duplicate_rate = self._analyze_duplicates(analysis_path)

            result = {
                "url": repo_url,
                "total_nloc": complexity_metrics["total_nloc"],
                "total_ccn": complexity_metrics["total_ccn"],
                "avg_ccn": complexity_metrics["avg_ccn"],
                "duplicate_rate": duplicate_rate,
            }

            return result

        finally:
            # Always cleanup temp directory if we created one
            if should_cleanup and temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temp directory: {temp_dir}")

    def _is_local_path(self, path: str) -> bool:
        """
        Check if the input is a local path (vs a URL).

        Parameters
        ----------
        path : str
            Path or URL to check

        Returns
        -------
        bool
            True if path is a local directory, False if it's a URL
        """
        # Check if it's an existing directory
        if os.path.isdir(path):
            return True

        url_schemes = ('http://', 'https://', 'git://', 'ssh://', 'git@')
        if path.startswith(url_schemes):
            return False

        # If not a URL and not an existing directory, treat as URL (will fail later if invalid)
        return False

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
