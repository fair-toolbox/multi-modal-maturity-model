"""FAIR compliance using howfairis."""

import logging
import os
from howfairis import Checker, Repo
from typing import Any

logger = logging.getLogger(__name__)


class HowfairisAnalyzer:
    """
    Collect FAIR compliance metrics using howfairis library.

    Parameters
    ----------
    repo_url : str
        GitHub or GitLab repository URL
    github_token : str | None
        GitHub API token for authenticated requests (optional)
    gitlab_token : str | None
        GitLab API token for authenticated requests (optional)
    """

    def __init__(
        self,
        repo_url: str,
        github_token: str | None = None,
        gitlab_token: str | None = None,
    ):
        self.github_token = github_token
        self.gitlab_token = gitlab_token
        self.repo_url = repo_url

    def analyze(self) -> dict[str, Any] | None:
        """
        Check FAIR compliance for a single repository.

        Returns
        -------
        dict[str, Any] | None
            Dictionary with FAIR compliance indicators:
            - repository: bool
            - license: bool
            - registry: bool
            - citation: bool
            - checklist: bool
        """
        logger.debug(f"Analyzing FAIR compliance for: {self.repo_url}")

        try:
            if self.github_token:
                os.environ["APIKEY_GITHUB"] = f"token:{self.github_token}"
            if self.gitlab_token:
                os.environ["APIKEY_GITLAB"] = f"token:{self.gitlab_token}"

            repo = Repo(self.repo_url)
            checker = Checker(repo, is_quiet=True)
            compliance = checker.check_five_recommendations()
            result = {
                "repository": compliance.repository,
                "license": compliance.license,
                "registry": compliance.registry,
                "citation": compliance.citation,
                "checklist": compliance.checklist,
            }
            logger.info(f"Successfully collected FAIR metrics for {self.repo_url}")
            return result

        except Exception:
            logger.error(
                f"Error occurred while analyzing FAIR compliance for {self.repo_url}"
            )
            return None
