"""
Tests for the MaturityAssessor pipeline.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from multi_modal_maturity_model.pipeline import MaturityAssessor
from multi_modal_maturity_model.core.models import (
    RepositoryMetrics,
    CodeQualityMetrics,
    ToolModel,
    Contributor,
)


@pytest.fixture
def assessor():
    """Create a MaturityAssessor instance."""
    return MaturityAssessor(
        github_token="test_token",
        gitlab_token="test_token",
        max_citations_corpus=1000,
    )


def test_assessor_initialization():
    """Test MaturityAssessor initialization."""
    assessor = MaturityAssessor(
        github_token="gh_token",
        gitlab_token="gl_token",
        max_citations_corpus=2000,
    )

    assert assessor.github_token == "gh_token"
    assert assessor.gitlab_token == "gl_token"
    assert assessor.max_citations_corpus == 2000
    assert assessor.mapper is not None


def test_detect_platform_github(assessor):
    """Test platform detection for GitHub."""
    assert assessor._detect_platform("https://github.com/owner/repo") == "github"
    assert assessor._detect_platform("owner/repo") is None
    assert assessor._detect_platform("owner/repo", "github") == "github"


def test_detect_platform_gitlab(assessor):
    """Test platform detection for GitLab."""
    assert assessor._detect_platform("group/project", "gitlab") == "gitlab"
    assert assessor._detect_platform("https://gitlab.com/owner/repo") == "gitlab"
    assert (
        assessor._detect_platform("https://gitlab.example.com/owner/repo") == "gitlab"
    )


def test_detect_platform_unknown(assessor):
    """Test platform detection for unknown platforms."""
    assert assessor._detect_platform("https://bitbucket.org/owner/repo") is None
    assert assessor._detect_platform("/local/path") is None


def test_extract_repo_identifier_github_url(assessor):
    """Test extracting repo identifier from GitHub URL."""
    result = assessor._extract_repo_identifier(
        "https://github.com/owner/repo", "github"
    )
    assert result == "owner/repo"

    result = assessor._extract_repo_identifier(
        "https://github.com/owner/repo.git", "github"
    )
    assert result == "owner/repo"


def test_extract_repo_identifier_short_format(assessor):
    """Test extracting repo identifier from short format."""
    result = assessor._extract_repo_identifier("owner/repo", "github")
    assert result == "owner/repo"


def test_normalize_repo_url_github(assessor):
    """Test normalizing GitHub repository URLs."""
    # Short format to full URL
    result = assessor._normalize_repo_url("owner/repo", "github")
    assert result == "https://github.com/owner/repo"

    # Already full URL
    result = assessor._normalize_repo_url("https://github.com/owner/repo", "github")
    assert result == "https://github.com/owner/repo"


def test_normalize_repo_url_gitlab(assessor):
    """Test normalizing GitLab repository URLs."""
    result = assessor._normalize_repo_url("owner/repo", "gitlab")
    assert result == "https://gitlab.com/owner/repo"


def test_assess_no_data_sources(assessor):
    """Test that assess raises error when no data sources provided."""
    with pytest.raises(ValueError, match="At least one data source"):
        assessor.assess()


@patch("multi_modal_maturity_model.pipeline.BioToolsClient")
def test_assess_with_biotools_only(mock_client, assessor):
    """Test assessment with only bio.tools data."""
    # Mock the client with data the real adapter can process
    mock_client_instance = Mock()
    mock_client.return_value = mock_client_instance
    mock_client_instance.fetch.return_value = {
        "biotoolsID": "test_tool",
        "name": "Test Tool",
        "function": [{"operation": [{"term": "Analysis"}]}],
        "topic": [{"term": "Biology"}],
    }

    # Run assessment - let real BioToolsAdapter process the data
    profile = assessor.assess(biotools_id="test_tool")

    # Verify
    assert profile is not None
    mock_client_instance.fetch.assert_called_once_with("test_tool")
    assert 0.0 <= profile.overall_score <= 1.0


@patch("multi_modal_maturity_model.pipeline.GitHubClient")
@patch("multi_modal_maturity_model.pipeline.resolve_repo_path")
@patch("multi_modal_maturity_model.pipeline.LizardCollector")
def test_assess_with_cloning(
    mock_lizard_collector,
    mock_resolve_repo_path,
    mock_github_client,
    assessor,
):
    """Test assessment with automatic repository cloning."""
    # Mock GitHub client with data the real adapter can process
    mock_github_instance = Mock()
    mock_github_client.return_value = mock_github_instance
    mock_github_instance.fetch.return_value = {
        "repo": {
            "html_url": "https://github.com/owner/repo",
            "full_name": "owner/repo",
            "default_branch": "main",
            "stargazers_count": 100,
            "forks_count": 10,
            "open_issues_count": 5,
            "license": {"name": "MIT"},
        },
        "contributors": [{"login": "user1", "contributions": 50}],
        "languages": {"Python": 1000},
        "closed_issues": [],
        "default_branch_protected": True,
    }

    # Mock repo cloning
    mock_resolve_repo_path.return_value = ("/tmp/test_repo", True)

    # Mock Lizard collector with data the real adapter can process
    mock_lizard_instance = Mock()
    mock_lizard_collector.return_value = mock_lizard_instance
    mock_lizard_instance.fetch.return_value = {
        "average": {
            "nloc": 25.5,
            "token_count": 150,
            "cyclomatic_complexity": 2.5,
        },
        "total_nloc": 1000,
        "total_ccn": 50,
        "function_list": [],
    }

    # Mock cleanup
    with patch("shutil.rmtree") as mock_rmtree:
        # Run assessment - let real adapters process the data
        profile = assessor.assess(
            repo_url="owner/repo",
            platform="github",
            collect_code_quality=True,
        )

        # Verify cloning happened
        mock_resolve_repo_path.assert_called_once_with("https://github.com/owner/repo")

        # Verify cleanup was called
        mock_rmtree.assert_called_once_with("/tmp/test_repo")

    assert profile is not None
    assert 0.0 <= profile.overall_score <= 1.0


@patch("multi_modal_maturity_model.pipeline.GitLabClient")
@patch("multi_modal_maturity_model.pipeline.resolve_repo_path")
@patch("multi_modal_maturity_model.pipeline.LizardCollector")
def test_assess_with_gitlab_cloning(
    mock_lizard_collector,
    mock_resolve_repo_path,
    mock_gitlab_client,
    assessor,
):
    """Test assessment with automatic GitLab repository cloning."""
    # Mock GitLab client with data the real adapter can process
    mock_gitlab_instance = Mock()
    mock_gitlab_client.return_value = mock_gitlab_instance
    mock_gitlab_instance.fetch.return_value = {
        "project": {
            "web_url": "https://gitlab.com/group/project",
            "path_with_namespace": "group/project",
            "default_branch": "main",
            "star_count": 50,
            "forks_count": 5,
            "open_issues_count": 3,
        },
        "contributors": [{"name": "User1", "commits": 25}],
        "languages": {"Python": 80.5, "JavaScript": 19.5},
        "closed_issues": [],
        "default_branch_protected": True,
    }

    # Mock repo cloning
    mock_resolve_repo_path.return_value = ("/tmp/test_gitlab_repo", True)

    # Mock Lizard collector with data the real adapter can process
    mock_lizard_instance = Mock()
    mock_lizard_collector.return_value = mock_lizard_instance
    mock_lizard_instance.fetch.return_value = {
        "average": {
            "nloc": 20.0,
            "token_count": 120,
            "cyclomatic_complexity": 2.0,
        },
        "total_nloc": 800,
        "total_ccn": 40,
        "function_list": [],
    }

    # Mock cleanup
    with patch("shutil.rmtree") as mock_rmtree:
        # Run assessment with GitLab platform - let real adapters process the data
        profile = assessor.assess(
            repo_url="group/project",
            platform="gitlab",
            collect_code_quality=True,
        )

        # Verify cloning happened with normalized GitLab URL
        mock_resolve_repo_path.assert_called_once_with(
            "https://gitlab.com/group/project"
        )

        # Verify cleanup was called
        mock_rmtree.assert_called_once_with("/tmp/test_gitlab_repo")

    assert profile is not None
    assert 0.0 <= profile.overall_score <= 1.0


def test_extract_repo_identifier_gitlab_nested(assessor):
    """Test extracting GitLab repository identifier with nested groups."""
    # Nested groups in URL
    result = assessor._extract_repo_identifier(
        "https://gitlab.com/group/subgroup/project", "gitlab"
    )
    # Should extract full path including nested groups
    assert result == "group/subgroup/project"

    # Short format with nested groups
    result = assessor._extract_repo_identifier("group/subgroup/project", "gitlab")
    assert result == "group/subgroup/project"

    # URL with .git suffix
    result = assessor._extract_repo_identifier(
        "https://gitlab.com/group/subgroup/project.git", "gitlab"
    )
    assert result == "group/subgroup/project"


def test_platform_parameter_ignored_with_url(assessor):
    """Test that platform parameter is ignored when full URL is provided."""
    # URL detection should take precedence over explicit platform
    platform = assessor._detect_platform(
        "https://github.com/owner/repo",
        explicit_platform="gitlab",  # This should be ignored
    )
    assert platform == "github"

    platform = assessor._detect_platform(
        "https://gitlab.com/group/project",
        explicit_platform="github",  # This should be ignored
    )
    assert platform == "gitlab"


def test_git_ssh_url_detection(assessor):
    """Test platform detection for git@ SSH URLs."""
    # GitHub SSH URL
    platform = assessor._detect_platform("git@github.com:owner/repo.git")
    assert platform == "github"

    # GitLab SSH URL
    platform = assessor._detect_platform("git@gitlab.com:group/project.git")
    assert platform == "gitlab"


@patch("multi_modal_maturity_model.pipeline.GitHubClient")
def test_assess_with_local_path(mock_client, assessor):
    """Test assessment using local repository path (no cloning)."""
    # Mock GitHub client with data the real adapter can process
    mock_client_instance = Mock()
    mock_client.return_value = mock_client_instance
    mock_client_instance.fetch.return_value = {
        "repo": {
            "html_url": "https://github.com/owner/repo",
            "full_name": "owner/repo",
            "default_branch": "main",
            "stargazers_count": 100,
            "forks_count": 10,
            "open_issues_count": 5,
            "license": None,
        },
        "contributors": [],
        "languages": {},
        "closed_issues": [],
        "default_branch_protected": False,
    }

    with patch("multi_modal_maturity_model.pipeline.LizardCollector") as mock_lizard:
        mock_lizard_instance = Mock()
        mock_lizard.return_value = mock_lizard_instance
        mock_lizard_instance.fetch.return_value = {
            "average": {
                "nloc": 25.0,
                "token_count": 150,
                "cyclomatic_complexity": 2.5,
            },
            "total_nloc": 1000,
            "total_ccn": 50,
            "function_list": [],
        }

        # Run assessment with local path - let real adapters process the data
        profile = assessor.assess(
            repo_url="owner/repo",
            repo_path="/local/path/to/repo",  # Local path provided
            collect_code_quality=True,
        )

        # Verify Lizard was called with local path
        mock_lizard_instance.fetch.assert_called_once_with("/local/path/to/repo")

    assert profile is not None


@patch("multi_modal_maturity_model.pipeline.BioToolsClient")
def test_assess_handles_collector_errors(mock_client, assessor):
    """Test that assessment continues when a collector fails."""
    # Mock client to raise an exception
    mock_client_instance = Mock()
    mock_client.return_value = mock_client_instance
    mock_client_instance.fetch.side_effect = Exception("API error")

    # Should not raise, should log warning and continue
    profile = assessor.assess(biotools_id="test_tool")

    assert profile is not None
    # Should have all zero scores since no data was collected
    assert profile.compatibility.score == 0.0


@patch("multi_modal_maturity_model.pipeline.HowfairisCollector")
def test_assess_with_fair_metrics(mock_howfairis, assessor):
    """Test assessment with FAIR compliance metrics."""
    mock_howfairis_instance = Mock()
    mock_howfairis.return_value = mock_howfairis_instance
    mock_howfairis_instance.fetch.return_value = {
        "repository": True,
        "license": True,
        "registry": False,
        "citation": True,
        "checklist": False,
    }

    with patch("multi_modal_maturity_model.pipeline.GitHubClient"):
        profile = assessor.assess(
            repo_url="owner/repo",
            collect_fair=True,
        )

    assert profile is not None
    # FAIR score should be > 0 since we have some FAIR indicators
    assert profile.fairness.score > 0.0


@patch("multi_modal_maturity_model.pipeline.EuropePMCClient")
def test_assess_with_citation_metrics(mock_client, assessor):
    """Test assessment with citation metrics."""
    mock_client_instance = Mock()
    mock_client.return_value = mock_client_instance
    mock_client_instance.fetch.return_value = {
        "citation_count": 50,
        "is_open_access": True,
    }

    profile = assessor.assess(pmid="12345678")

    assert profile is not None
    mock_client_instance.fetch.assert_called_once_with("12345678")
    # Scientific impact should be > 0 with citations
    assert profile.scientific_impact.score > 0.0


def test_assess_skip_code_quality(assessor):
    """Test that code quality collection can be skipped."""
    with patch("multi_modal_maturity_model.pipeline.resolve_repo_path") as mock_resolve:
        profile = assessor.assess(
            repo_url="owner/repo",
            collect_code_quality=False,  # Skip code analysis
        )

        # Cloning should not happen
        mock_resolve.assert_not_called()

    assert profile is not None
