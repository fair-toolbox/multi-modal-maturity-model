"""
Tests for the MaturityService.
"""

import pytest
from unittest.mock import Mock, patch

from multi_modal_maturity_model.service import MaturityService
from multi_modal_maturity_model.models import (
    RepositoryMetrics,
    CodeQualityMetrics,
    ToolModel,
    Contributor,
    DimensionScore,
)


@pytest.fixture
def service():
    """Create a MaturityService instance."""
    return MaturityService(
        github_token="test_token",
        gitlab_token="test_token",
        max_citations_corpus=1000,
    )


@pytest.fixture
def sample_repository_metrics():
    """Create sample RepositoryMetrics with all required fields."""
    return RepositoryMetrics(
        platform="github",
        url="https://github.com/owner/repo",
        repo="owner/repo",
        default_branch="main",
        stars=100,
        forks=10,
        open_issues=5,
        avg_time_to_close_days=10.5,
        default_branch_is_protected=True,
        languages=["Python"],
        last_commit_date="2026-04-01T00:00:00Z",
        contributors=[Contributor(login="user1", total_commits=50)],
        has_license=True,
        has_workflow_integration=True,
        has_distribution_support=True,
        has_security_policy=True,
        has_security_scanning=True,
        inverse_simpson_index=1.5,
    )


def test_service_initialization():
    """Test MaturityService initialization."""
    service = MaturityService(
        github_token="gh_token",
        gitlab_token="gl_token",
        max_citations_corpus=2000,
    )

    assert service.github_token == "gh_token"
    assert service.gitlab_token == "gl_token"
    assert service.max_citations_corpus == 2000
    assert service.mapper is not None


def test_evaluate_no_data_sources(service):
    """Test that evaluate raises error when no data sources provided."""
    with pytest.raises(ValueError, match="Repository URL is required."):
        service.evaluate()


@patch("multi_modal_maturity_model.service.MaturityService._collect_howfairis")
@patch("multi_modal_maturity_model.service.MaturityService._collect_repository")
@patch("multi_modal_maturity_model.service.MaturityService._collect_code_quality")
def test_evaluate_with_repository_and_code_quality(
    mock_collect_code_quality,
    mock_collect_repository,
    mock_collect_howfairis,
    service,
    sample_repository_metrics,
):
    """Test evaluation with repository and code quality metrics."""
    # Mock repository collection
    mock_collect_repository.return_value = sample_repository_metrics

    # Mock code quality collection
    mock_collect_code_quality.return_value = CodeQualityMetrics(
        total_nloc=1000,
        total_ccn=50,
        avg_ccn=2.5,
        duplicate_rate=0.1,
    )

    # Mock howfairis collection
    mock_collect_howfairis.return_value = None

    # Run evaluation
    profile = service.evaluate(
        repo_url="https://github.com/owner/repo",
        include_code_quality=True,
    )

    # Verify collections were called
    mock_collect_repository.assert_called_once()
    mock_collect_code_quality.assert_called_once()

    assert profile is not None
    assert profile.overall_score.score is not None


@patch("multi_modal_maturity_model.service.MaturityService._collect_howfairis")
@patch("multi_modal_maturity_model.service.MaturityService._collect_repository")
@patch("multi_modal_maturity_model.service.MaturityService._collect_code_quality")
def test_evaluate_with_gitlab(
    mock_collect_code_quality,
    mock_collect_repository,
    mock_collect_howfairis,
    service,
):
    """Test evaluation with GitLab repository."""
    # Mock repository collection
    mock_collect_repository.return_value = RepositoryMetrics(
        platform="gitlab",
        url="https://gitlab.com/group/project",
        repo="group/project",
        default_branch="main",
        stars=50,
        forks=5,
        open_issues=3,
        avg_time_to_close_days=8.0,
        default_branch_is_protected=True,
        languages=["Python", "JavaScript"],
        last_commit_date="2026-04-01T00:00:00Z",
        contributors=[Contributor(login="user1", total_commits=25)],
        has_license=True,
        has_workflow_integration=False,
        has_distribution_support=False,
        has_security_policy=False,
        has_security_scanning=False,
        inverse_simpson_index=1.5,
    )

    # Mock code quality collection
    mock_collect_code_quality.return_value = CodeQualityMetrics(
        total_nloc=800,
        total_ccn=40,
        avg_ccn=2.0,
        duplicate_rate=0.05,
    )

    # Mock howfairis collection
    mock_collect_howfairis.return_value = None

    # Run evaluation with GitLab
    profile = service.evaluate(
        repo_url="https://gitlab.com/group/project",
        include_code_quality=True,
    )

    assert profile is not None
    assert profile.overall_score.score is not None


@patch("multi_modal_maturity_model.service.MaturityService._collect_howfairis")
@patch("multi_modal_maturity_model.service.MaturityService._collect_repository")
@patch("multi_modal_maturity_model.service.MaturityService._collect_code_quality")
def test_evaluate_with_local_path(
    mock_collect_code_quality,
    mock_collect_repository,
    mock_collect_howfairis,
    service,
    sample_repository_metrics,
):
    """Test evaluation using local repository path."""
    # Mock repository collection
    mock_collect_repository.return_value = sample_repository_metrics

    # Mock code quality collection
    mock_collect_code_quality.return_value = CodeQualityMetrics(
        total_nloc=1000,
        total_ccn=50,
        avg_ccn=2.5,
        duplicate_rate=0.1,
    )

    # Mock howfairis collection
    mock_collect_howfairis.return_value = None

    # Run evaluation with local path
    profile = service.evaluate(
        repo_url="https://github.com/owner/repo",
        repo_path="/local/path/to/repo",
        include_code_quality=True,
    )

    # Verify code quality was called with local path
    assert mock_collect_code_quality.called
    call_args = mock_collect_code_quality.call_args
    assert call_args[0][0] == "https://github.com/owner/repo"  # repo_url argument
    assert call_args[0][1] == "/local/path/to/repo"  # repo_path argument

    assert profile is not None


@patch("multi_modal_maturity_model.service.MaturityService._collect_howfairis")
@patch("multi_modal_maturity_model.service.MaturityService._collect_repository")
def test_evaluate_handles_collector_errors(
    mock_collect_repository, mock_collect_howfairis, service
):
    """Test that evaluation continues when a collector fails."""
    # Mock collection to return None (failure)
    mock_collect_repository.return_value = None
    mock_collect_howfairis.return_value = None

    # Evaluation should complete even when repository metrics fail
    profile = service.evaluate(repo_url="https://github.com/owner/repo")

    # Profile should be created but with None score for dimensions requiring repo metrics
    assert profile is not None
    assert profile.sustainability.score is None


@patch("multi_modal_maturity_model.service.MaturityService._collect_howfairis")
@patch("multi_modal_maturity_model.service.MaturityService._collect_code_quality")
@patch("multi_modal_maturity_model.service.MaturityService._collect_repository")
def test_evaluate_skip_code_quality(
    mock_collect_repository,
    mock_collect_code_quality,
    mock_collect_howfairis,
    service,
    sample_repository_metrics,
):
    """Test that code quality collection can be skipped."""
    mock_collect_repository.return_value = sample_repository_metrics
    mock_collect_howfairis.return_value = None

    profile = service.evaluate(
        repo_url="https://github.com/owner/repo",
        include_code_quality=False,  # Skip code analysis
    )

    # Code quality collection should not be called
    mock_collect_code_quality.assert_not_called()

    assert profile is not None


@patch("multi_modal_maturity_model.service.MaturityService._collect_howfairis")
@patch("multi_modal_maturity_model.service.MaturityService._collect_biotools")
@patch("multi_modal_maturity_model.service.MaturityService._collect_repository")
def test_evaluate_with_biotools_id(
    mock_collect_repository,
    mock_collect_biotools,
    mock_collect_howfairis,
    service,
    sample_repository_metrics,
):
    """Test evaluation with bio.tools ID."""
    mock_collect_repository.return_value = sample_repository_metrics
    mock_collect_howfairis.return_value = None

    mock_tool_model = Mock(spec=ToolModel)
    mock_tool_model.biotools_id = "test_tool"
    mock_tool_model.function = []
    mock_collect_biotools.return_value = mock_tool_model

    profile = service.evaluate(
        biotools_id="test_tool", repo_url="https://github.com/owner/repo"
    )

    assert profile is not None
    mock_collect_biotools.assert_called_once()


def test_get_repository_client_and_adapter(service):
    """Test getting the correct client and adapter for platform."""
    # Test GitHub
    client, adapter = service._get_repository_client_and_adapter("github")
    assert client is service.github_client
    assert adapter is not None

    # Test GitLab
    client, adapter = service._get_repository_client_and_adapter("gitlab")
    assert client is service.gitlab_client
    assert adapter is not None

    # Test unknown platform
    client, adapter = service._get_repository_client_and_adapter("unknown")
    assert client is None
    assert adapter is None
