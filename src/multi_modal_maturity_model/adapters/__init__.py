"""
Adapters transform raw client data into core domain models.
"""

from .biotools_adapter import BioToolsAdapter
from .github_adapter import GitHubAdapter
from .gitlab_adapter import GitLabAdapter

__all__ = ["BioToolsAdapter", "GitHubAdapter", "GitLabAdapter"]
