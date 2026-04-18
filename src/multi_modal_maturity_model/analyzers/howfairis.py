"""
FAIR compliance usind howfairis.
"""

import logging
from typing import Any

from howfairis import Checker, Repo


logger = logging.getLogger(__name__)


class HowfairisAnalyzer:
    """
    Collect FAIR compliance metrics using howfairis library.
    """

    def __init__(self):
        """Initialize howfairis client."""

    def analyze(self, repo_url: str) -> dict[str, Any]:
        """
        Assess FAIR compliance for a single repository.

        Parameters
        ----------
        repo_url : str
            GitHub or GitLab repository URL

        Returns
        -------
        dict[str, Any]
            Dictionary with FAIR compliance indicators:
            - repository: bool | None
            - license: bool | None
            - registry: bool | None
            - citation: bool | None
            - checklist: bool | None
        """
        logger.debug(f"Assessing FAIR compliance for: {repo_url}")

        try:
            repo = Repo(repo_url)
            checker = Checker(repo, is_quiet=True)
            compliance = checker.check_five_recommendations()

            result = {
                "repository": compliance.repository,
                "license": compliance.license,
                "registry": compliance.registry,
                "citation": compliance.citation,
                "checklist": compliance.checklist,
            }

            logger.info(f"Successfully assessed {repo_url}")
            return result

        except Exception as e:
            logger.error(f"Error assessing {repo_url}: {e}")
            raise
