"""
Adapters transform raw collector data into core domain models.
"""

from multi_modal_maturity_model.adapters.github_adapter import GitHubAdapter
from multi_modal_maturity_model.adapters.gitlab_adapter import GitLabAdapter

__all__ = ["GitHubAdapter", "GitLabAdapter"]
