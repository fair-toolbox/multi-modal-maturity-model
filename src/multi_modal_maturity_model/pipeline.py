"""High-level pipeline for maturity analysis of research software."""

import asyncio

from .analyzers import HowfairisAnalyzer, LizardAnalyzer
from .clients import BioToolsClient, GitHubClient, GitLabClient, OpenAlexClient


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
    ):
        self.github_token = github_token
        self.gitlab_token = gitlab_token

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

        # TODO: clone repository if repo_path is not provided
        # lizard_analyzer = LizardAnalyzer(self.repo_path)
        # results_by_source["lizard"] = lizard_analyzer.analyze()

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

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        return {
            source: result
            for source, result in zip(tasks.keys(), results)
            if not isinstance(result, Exception)
        }


def detect_platform(url: str) -> str:
    """Detect repository platform from URL."""
    if url.startswith(("http://", "https://", "git@")):
        url_lower = url.lower()
        if "github.com" in url_lower:
            return "github"
        elif "gitlab.com" in url_lower:
            return "gitlab"
    raise ValueError("Unsupported repository URL.")
