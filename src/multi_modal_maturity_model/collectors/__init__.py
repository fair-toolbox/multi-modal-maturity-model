"""
Data fetching and collection from external sources.
Contains API calls, tool invocations, raw data fetching.
"""

from .biotools import BioToolsClient
from .europe_pmc import EuropePMCClient
from .github import GitHubClient
from .gitlab import GitLabClient
from .howfairis import HowfairisCollector
from .lizard import LizardCollector

__all__ = [
    "BioToolsClient",
    "EuropePMCClient",
    "GitHubClient",
    "GitLabClient",
    "HowfairisCollector",
    "LizardCollector",
]
