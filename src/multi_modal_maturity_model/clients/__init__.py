"""
Data fetching and collection from external sources.
Contains API calls, tool invocations, raw data fetching.
"""

from .biotools import BioToolsClient
from .europe_pmc import EuropePMCClient
from .github import GitHubClient
from .gitlab import GitLabClient
from .semantic_scholar import SemanticScholarClient
from .edam_cache import edam_cache

__all__ = [
    "BioToolsClient",
    "EuropePMCClient",
    "GitHubClient",
    "GitLabClient",
    "SemanticScholarClient",
    "edam_cache",
]
