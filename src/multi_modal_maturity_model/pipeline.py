"""High-level pipeline for maturity analysis of research software."""

import asyncio
import logging

from .analyzers import HowfairisAnalyzer, LizardAnalyzer
from .clients import (
    AltmetricClient,
    BioToolsClient,
    EuropePMCClient,
    GitHubClient,
    GitLabClient,
    OpenAlexClient,
)
from .git_utils import detect_platform, temporary_clone

logger = logging.getLogger(__name__)


class MaturityPipeline:
    """
    High-level pipeline for maturity analysis of research software.

    Parameters
    ----------
    repo_url : str
        URL of the repository to analyze.
    github_token : str | None, optional
        GitHub API token for authentication (default: None).
    gitlab_token : str | None, optional
        GitLab API token for authentication (default: None).
    """

    def __init__(
        self,
        github_token: str | None = None,
        gitlab_token: str | None = None,
        altmetric_api_key: str | None = None,
    ):
        self.github_token = github_token
        self.gitlab_token = gitlab_token
        self.altmetric_api_key = altmetric_api_key

    async def run(
        self,
        repo_url: str,
        repo_path: str | None = None,
        biotools_id: str | None = None,
        dois: list[str] | None = None,
    ) -> dict[str, dict]:
        """
        Run the maturity analysis pipeline.

        Returns
        -------
        dict[str, dict]
            Dictionary containing results from all analyzers.
        """

        results_by_source = await self._fetch_all(repo_url, biotools_id, dois)

        howfairis_analyzer = HowfairisAnalyzer(
            self.repo_url, self.github_token, self.gitlab_token
        )
        results_by_source["howfairis"] = howfairis_analyzer.analyze()

        if not repo_path:
            with temporary_clone(repo_url) as temp_path:
                lizard_analyzer = LizardAnalyzer(temp_path)
                results_by_source["lizard"] = lizard_analyzer.analyze()
        else:
            lizard_analyzer = LizardAnalyzer(repo_path)
            results_by_source["lizard"] = lizard_analyzer.analyze()

        return results_by_source

    async def _collect_all(
        self,
        repo_url: str,
        biotools_id: str | None = None,
        dois: list[str] | None = None,
    ) -> dict[str, dict]:
        """Collect data from all sources in parallel."""
        tasks = {}

        platform = detect_platform(repo_url)

        if platform == "github":
            github_client = GitHubClient(repo_url, self.github_token)
            tasks["github"] = await github_client.fetch()
        elif platform == "gitlab":
            gitlab_client = GitLabClient(repo_url, self.gitlab_token)
            tasks["gitlab"] = await gitlab_client.fetch()

        if biotools_id:
            biotools_client = BioToolsClient(biotools_id=biotools_id)
            tasks["biotools"] = biotools_client.fetch()

        if dois:
            openalex_client = OpenAlexClient(dois=dois)
            tasks["openalex"] = await openalex_client.fetch()

            europepmc_client = EuropePMCClient(dois=dois)
            tasks["europepmc"] = await europepmc_client.fetch()

            if self.altmetric_api_key:
                altmetric_client = AltmetricClient(
                    dois=dois, api_key=self.altmetric_api_key
                )
                tasks["altmetric"] = await altmetric_client.fetch()

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        return {
            source: result
            for source, result in zip(tasks.keys(), results)
            if not isinstance(result, Exception)
        }
