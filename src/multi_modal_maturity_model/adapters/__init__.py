"""
Adapters transform raw client data into core domain models.
"""

from .base_repo_adapter import BaseRepositoryAdapter
from .biotools_adapter import BioToolsAdapter
from .github_adapter import GitHubAdapter
from .gitlab_adapter import GitLabAdapter

__all__ = ["BaseRepositoryAdapter", "BioToolsAdapter", "GitHubAdapter", "GitLabAdapter"]
