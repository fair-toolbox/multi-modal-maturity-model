"""
FAIR compliance usind howfairis.
"""

import logging
import os
from typing import Any

from howfairis import Checker, Repo


logger = logging.getLogger(__name__)


class HowfairisAnalyzer:
    """
    Collect FAIR compliance metrics using howfairis library.
    """

    def __init__(
        self, github_token: str | None = None, gitlab_token: str | None = None
    ):
        """
        Initialize howfairis client.

        Parameters
        ----------
        github_token : str | None
            GitHub API token for authenticated requests
        gitlab_token : str | None
            GitLab API token for authenticated requests
        """
        self.github_token = github_token
        self.gitlab_token = gitlab_token

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
        logger.debug(f"Analyzing FAIR compliance for: {repo_url}")

        try:
            if self.github_token:
                os.environ["APIKEY_GITHUB"] = f"token:{self.github_token}"
            if self.gitlab_token:
                os.environ["APIKEY_GITLAB"] = f"token:{self.gitlab_token}"

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
            logger.info(f"Successfully collected FAIR metrics for {repo_url}")
            return result

        except Exception:
            raise
