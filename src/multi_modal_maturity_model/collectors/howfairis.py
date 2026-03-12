"""
FAIR compliance usind howfairis.
"""

import logging
from typing import Any

from howfairis import Checker, Repo


logger = logging.getLogger(__name__)


class HowfairisClient:
    """
    Collect FAIR compliance metrics using howfairis library.
    """

    def __init__(self, rate_limit_seconds: int = 60):
        """
        Parameters
        ----------
        rate_limit_seconds : int
            Seconds to wait between API calls to avoid rate limiting
        """
        self.rate_limit_seconds = rate_limit_seconds

    def fetch(self, repo_url: str) -> dict[str, Any]:
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
            checker = Checker(repo)
            checker.check_five_recommendations()

            result = {
                "repository": checker.has_open_repository,
                "license": checker.has_license,
                "registry": checker.has_registry,
                "citation": checker.has_citation,
                "checklist": checker.has_checklist,
            }

            logger.info(f"Successfully assessed {repo_url}")
            return result

        except Exception as e:
            logger.error(f"Error assessing {repo_url}: {e}")
            raise
