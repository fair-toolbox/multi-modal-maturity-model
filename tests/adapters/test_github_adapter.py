"""
Tests for GitHubAdapter.
"""

import pytest
from datetime import datetime, timedelta

from multi_modal_maturity_model.adapters.github_adapter import (
    GitHubAdapter,
    transform_contributors,
    extract_languages,
)
from multi_modal_maturity_model.adapters.adapters_utils import (
    calculate_avg_time_to_close,
    detect_distribution_support,
    detect_security_policy,
    detect_security_scanning,
    detect_workflow_support,
)
from multi_modal_maturity_model.core.models import Contributor, RepositoryMetrics


# ----------------------------
# Helper function tests
# ----------------------------


def test_transform_contributors():
    raw = [
        {"login": "alice", "contributions": 10},
        {"login": "bob", "contributions": 5},
    ]
    result = transform_contributors(raw)
    assert len(result) == 2
    assert result[0] == Contributor(login="alice", total_commits=10)
    assert result[1] == Contributor(login="bob", total_commits=5)


def test_transform_contributors_empty():
    result = transform_contributors([])
    assert result == []


def test_transform_contributors_none():
    result = transform_contributors(None)
    assert result == []


def test_extract_languages():
    langs = {"Python": 75000, "JavaScript": 25000, "Shell": 5000}
    result = extract_languages(langs)
    assert set(result) == {"Python", "JavaScript", "Shell"}


def test_extract_languages_empty():
    result = extract_languages({})
    assert result == []


def test_extract_languages_none():
    result = extract_languages(None)
    assert result == []


def test_calculate_avg_time_to_close_github_dict_format():
    """Test avg time calculation with GitHub dict format."""
    issues = [
        {
            "created_at": "2024-01-01T00:00:00Z",
            "closed_at": "2024-01-03T00:00:00Z",
        },  # 2 days
        {
            "created_at": "2024-01-05T00:00:00Z",
            "closed_at": "2024-01-11T00:00:00Z",
        },  # 6 days
    ]
    avg_days = calculate_avg_time_to_close(issues)
    assert avg_days == 4.0


def test_calculate_avg_time_to_close_none():
    """Test avg time calculation with None."""
    result = calculate_avg_time_to_close(None)
    assert result is None


def test_calculate_avg_time_to_close_empty():
    """Test avg time calculation with empty list."""
    result = calculate_avg_time_to_close([])
    assert result is None


def test_calculate_avg_time_to_close_single_issue():
    """Test avg time calculation with single issue."""
    issues = [
        {
            "created_at": "2024-01-01T00:00:00Z",
            "closed_at": "2024-01-06T00:00:00Z",
        }
    ]
    result = calculate_avg_time_to_close(issues)
    assert result == 5.0


def test_calculate_avg_time_to_close_missing_dates():
    """Test avg time calculation with missing dates."""
    issues = [
        {
            "created_at": "2024-01-01T00:00:00Z",
            "closed_at": None,  # Missing closed_at
        },
        {
            "created_at": None,  # Missing created_at
            "closed_at": "2024-01-05T00:00:00Z",
        },
        {
            "created_at": "2024-01-01T00:00:00Z",
            "closed_at": "2024-01-11T00:00:00Z",
        },  # Valid: 10 days
    ]
    result = calculate_avg_time_to_close(issues)
    assert result == 10.0


def test_calculate_avg_time_to_close_invalid_format():
    """Test avg time calculation with invalid date formats."""
    issues = [
        {
            "created_at": "invalid-date",
            "closed_at": "2024-01-05T00:00:00Z",
        },
        {
            "created_at": "2024-01-01T00:00:00Z",
            "closed_at": "2024-01-11T00:00:00Z",
        },  # Valid: 10 days
    ]
    result = calculate_avg_time_to_close(issues)
    assert result == 10.0


def test_calculate_avg_time_to_close_all_invalid():
    """Test avg time calculation when all issues have invalid dates."""
    issues = [
        {
            "created_at": "invalid",
            "closed_at": "also-invalid",
        },
        {
            "created_at": None,
            "closed_at": None,
        },
    ]
    result = calculate_avg_time_to_close(issues)
    assert result is None


def test_calculate_avg_time_to_close_fractional_days():
    """Test avg time calculation with fractional days."""
    issues = [
        {
            "created_at": "2024-01-01T00:00:00Z",
            "closed_at": "2024-01-01T12:00:00Z",
        },  # 0.5 days
        {
            "created_at": "2024-01-01T00:00:00Z",
            "closed_at": "2024-01-02T06:00:00Z",
        },  # 1.25 days
    ]
    result = calculate_avg_time_to_close(issues)
    # Average: (0.5 + 1.25) / 2 = 0.875, rounded to 0.88
    assert result == 0.88


def test_calculate_avg_time_to_close_with_timezone():
    """Test avg time calculation with timezone-aware dates."""
    issues = [
        {
            "created_at": "2024-01-01T00:00:00+00:00",
            "closed_at": "2024-01-03T00:00:00+00:00",
        }
    ]
    result = calculate_avg_time_to_close(issues)
    assert result == 2.0


def test_calculate_avg_time_to_close_same_day():
    """Test avg time calculation for issues closed same day."""
    issues = [
        {
            "created_at": "2024-01-01T09:00:00Z",
            "closed_at": "2024-01-01T17:00:00Z",
        }  # 8 hours = 0.33 days
    ]
    result = calculate_avg_time_to_close(issues)
    assert result == 0.33


# ----------------------------
# GitHubAdapter tests
# ----------------------------


class TestGitHubAdapter:
    """Test suite for GitHubAdapter class."""

    @pytest.fixture
    def complete_raw_data(self):
        """Sample complete raw data from GitHub collector."""
        return {
            "repo": {
                "html_url": "https://github.com/owner/test-repo",
                "full_name": "owner/test-repo",
                "default_branch": "main",
                "stargazers_count": 150,
                "forks_count": 25,
                "open_issues_count": 10,
                "license": {"key": "mit", "name": "MIT License"},
            },
            "contributors": [
                {"login": "user1", "contributions": 50},
                {"login": "user2", "contributions": 30},
                {"login": "user3", "contributions": 15},
            ],
            "closed_issues": [
                {
                    "number": 1,
                    "title": "Issue 1",
                    "created_at": "2024-01-01T00:00:00Z",
                    "closed_at": "2024-01-03T00:00:00Z",
                },
                {
                    "number": 2,
                    "title": "Issue 2",
                    "created_at": "2024-01-05T00:00:00Z",
                    "closed_at": "2024-01-11T00:00:00Z",
                },
            ],
            "languages": {"Python": 75000, "JavaScript": 25000, "Shell": 5000},
            "default_branch_protected": True,
            "contents": [
                {"path": "workflow/main.nf", "type": "blob"},
                {"path": "Dockerfile", "type": "blob"},
                {"path": "SECURITY.md", "type": "blob"},
                {"path": ".github/dependabot.yml", "type": "blob"},
            ],
        }

    @pytest.fixture
    def minimal_raw_data(self):
        """Minimal raw data with only required fields."""
        return {
            "repo": {
                "html_url": "https://github.com/owner/minimal-repo",
                "full_name": "owner/minimal-repo",
                "default_branch": "master",
                "stargazers_count": 0,
                "forks_count": 0,
                "open_issues_count": 0,
            },
        }

    def test_to_repository_metrics_complete_data(self, complete_raw_data):
        """Test conversion with complete data."""
        result = GitHubAdapter.to_repository_metrics(complete_raw_data)

        assert isinstance(result, RepositoryMetrics)
        assert result.platform == "github"
        assert result.url == "https://github.com/owner/test-repo"
        assert result.repo == "owner/test-repo"
        assert result.default_branch == "main"
        assert result.stars == 150
        assert result.forks == 25
        assert result.open_issues == 10
        assert result.has_license is True
        assert result.default_branch_is_protected is True
        assert result.has_workflow_integration is True
        assert result.has_distribution_support is True
        assert result.has_security_policy is True
        assert result.has_security_scanning is True

    def test_to_repository_metrics_contributors(self, complete_raw_data):
        """Test contributor transformation."""
        result = GitHubAdapter.to_repository_metrics(complete_raw_data)

        assert len(result.contributors) == 3
        assert all(isinstance(c, Contributor) for c in result.contributors)
        assert result.contributors[0].login == "user1"
        assert result.contributors[0].total_commits == 50
        assert result.contributors[1].login == "user2"
        assert result.contributors[1].total_commits == 30
        assert result.contributors[2].login == "user3"
        assert result.contributors[2].total_commits == 15

    def test_to_repository_metrics_languages(self, complete_raw_data):
        """Test language extraction."""
        result = GitHubAdapter.to_repository_metrics(complete_raw_data)

        assert len(result.languages) == 3
        assert "Python" in result.languages
        assert "JavaScript" in result.languages
        assert "Shell" in result.languages

    def test_to_repository_metrics_avg_time_to_close(self, complete_raw_data):
        """Test average time to close calculation."""
        result = GitHubAdapter.to_repository_metrics(complete_raw_data)

        # Issue 1: 2 days, Issue 2: 6 days, Average: 4 days
        assert result.avg_time_to_close_days == 4.0

    def test_to_repository_metrics_minimal_data(self, minimal_raw_data):
        """Test conversion with minimal data."""
        result = GitHubAdapter.to_repository_metrics(minimal_raw_data)

        assert result.platform == "github"
        assert result.url == "https://github.com/owner/minimal-repo"
        assert result.stars == 0
        assert result.forks == 0
        assert result.contributors == []
        assert result.languages == []
        assert result.has_license is False
        assert result.avg_time_to_close_days is None
        assert result.default_branch_is_protected is None
        assert result.has_workflow_integration is None
        assert result.has_distribution_support is None
        assert result.has_security_policy is None
        assert result.has_security_scanning is None

    def test_to_repository_metrics_no_license(self, complete_raw_data):
        """Test handling of repositories without license."""
        complete_raw_data["repo"]["license"] = None
        result = GitHubAdapter.to_repository_metrics(complete_raw_data)

        assert result.has_license is False

    def test_to_repository_metrics_empty_contributors(self, complete_raw_data):
        """Test handling of empty contributors list."""
        complete_raw_data["contributors"] = []
        result = GitHubAdapter.to_repository_metrics(complete_raw_data)

        assert result.contributors == []

    def test_to_repository_metrics_none_contributors(self, complete_raw_data):
        """Test handling of None contributors."""
        complete_raw_data["contributors"] = None
        result = GitHubAdapter.to_repository_metrics(complete_raw_data)

        assert result.contributors == []

    def test_to_repository_metrics_empty_languages(self, complete_raw_data):
        """Test handling of empty languages."""
        complete_raw_data["languages"] = {}
        result = GitHubAdapter.to_repository_metrics(complete_raw_data)

        assert result.languages == []

    def test_to_repository_metrics_none_languages(self, complete_raw_data):
        """Test handling of None languages."""
        complete_raw_data["languages"] = None
        result = GitHubAdapter.to_repository_metrics(complete_raw_data)

        assert result.languages == []

    def test_to_repository_metrics_protected_branch_false(self, complete_raw_data):
        """Test handling when default branch is not protected."""
        complete_raw_data["default_branch_protected"] = False
        result = GitHubAdapter.to_repository_metrics(complete_raw_data)

        assert result.default_branch_is_protected is False

    def test_to_repository_metrics_protected_branch_none(self, complete_raw_data):
        """Test handling when branch protection status is unknown."""
        complete_raw_data["default_branch_protected"] = None
        result = GitHubAdapter.to_repository_metrics(complete_raw_data)

        assert result.default_branch_is_protected is None


def test_detect_workflow_support_from_repository_tree():
    repository_tree = [
        {"path": "workflow/main.nf", "type": "blob"},
        {"path": "docs/index.md", "type": "blob"},
    ]

    assert detect_workflow_support(repository_tree) is True


def test_detect_distribution_support_from_repository_tree():
    repository_tree = [
        {"path": "containers/Dockerfile", "type": "blob"},
        {"path": "pyproject.toml", "type": "blob"},
    ]

    assert detect_distribution_support(repository_tree) is True


def test_detect_security_policy_from_repository_tree():
    repository_tree = [
        {"path": ".github/SECURITY.md", "type": "blob"},
        {"path": "docs/index.md", "type": "blob"},
    ]

    assert detect_security_policy(repository_tree) is True


def test_detect_security_scanning_from_repository_tree():
    repository_tree = [
        {"path": ".github/workflows/codeql-analysis.yml", "type": "blob"},
        {"path": "docs/index.md", "type": "blob"},
    ]

    assert detect_security_scanning(repository_tree) is True
