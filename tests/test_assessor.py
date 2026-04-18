"""
Tests for the MaturityAssessor.
"""

import pytest
from unittest.mock import Mock, patch

from multi_modal_maturity_model.assessor import MaturityAssessor
from multi_modal_maturity_model.models import (
    RepositoryMetrics,
    CodeQualityMetrics,
    ToolModel,
    Contributor,
    DimensionScore,
)


@pytest.fixture
def assessor():
    """Create a MaturityAssessor instance."""
    return MaturityAssessor(
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


def test_assess_no_data_sources(assessor):
    """Test that assess raises error when no data sources provided."""
    with pytest.raises(ValueError, match="Repository URL is required."):
        assessor.assess()


@patch("multi_modal_maturity_model.assessor.collect_repository")
@patch("multi_modal_maturity_model.assessor.collect_code_quality")
def test_assess_with_repository_and_code_quality(
    mock_collect_code_quality,
    mock_collect_repository,
    assessor,
    sample_repository_metrics,
):
    """Test assessment with repository and code quality metrics."""
    # Mock repository collection
    mock_collect_repository.return_value = sample_repository_metrics

    # Mock code quality collection
    mock_collect_code_quality.return_value = CodeQualityMetrics(
        total_nloc=1000,
        total_ccn=50,
        avg_ccn=2.5,
        duplicate_rate=0.1,
    )

    # Run assessment
    profile = assessor.assess(
        repo_url="https://github.com/owner/repo",
        include_code_quality=True,
    )

    # Verify collections were called
    mock_collect_repository.assert_called_once()
    mock_collect_code_quality.assert_called_once()

    assert profile is not None
    assert profile.overall_score.score is not None


@patch("multi_modal_maturity_model.assessor.collect_repository")
@patch("multi_modal_maturity_model.assessor.collect_code_quality")
def test_assess_with_gitlab(
    mock_collect_code_quality,
    mock_collect_repository,
    assessor,
):
    """Test assessment with GitLab repository."""
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
    )

    # Mock code quality collection
    mock_collect_code_quality.return_value = CodeQualityMetrics(
        total_nloc=800,
        total_ccn=40,
        avg_ccn=2.0,
        duplicate_rate=0.05,
    )

    # Run assessment with GitLab
    profile = assessor.assess(
        repo_url="https://gitlab.com/group/project",
        include_code_quality=True,
    )

    assert profile is not None
    assert profile.overall_score.score is not None


@patch("multi_modal_maturity_model.assessor.collect_repository")
@patch("multi_modal_maturity_model.assessor.collect_code_quality")
def test_assess_with_local_path(
    mock_collect_code_quality,
    mock_collect_repository,
    assessor,
    sample_repository_metrics,
):
    """Test assessment using local repository path."""
    # Mock repository collection
    mock_collect_repository.return_value = sample_repository_metrics

    # Mock code quality collection
    mock_collect_code_quality.return_value = CodeQualityMetrics(
        total_nloc=1000,
        total_ccn=50,
        avg_ccn=2.5,
        duplicate_rate=0.1,
    )

    # Run assessment with local path
    profile = assessor.assess(
        repo_url="owner/repo",
        repo_path="/local/path/to/repo",
        platform="github",
        include_code_quality=True,
    )

    # Verify code quality was called with local path
    assert mock_collect_code_quality.called
    call_args = mock_collect_code_quality.call_args
    assert call_args[0][2] == "/local/path/to/repo"  # repo_path argument

    assert profile is not None


@patch("multi_modal_maturity_model.assessor.collect_repository")
def test_assess_handles_collector_errors(mock_collect_repository, assessor):
    """Test that assessment continues when a collector fails."""
    # Mock collection to return None (failure)
    mock_collect_repository.return_value = None

    # Assessment should complete even when repository metrics fail
    profile = assessor.assess(repo_url="https://github.com/owner/repo")

    # Profile should be created but with None score for dimensions requiring repo metrics
    assert profile is not None
    assert profile.sustainability.score is None


@patch("multi_modal_maturity_model.assessor.collect_howfairis")
@patch("multi_modal_maturity_model.assessor.collect_repository")
def test_assess_with_fair_metrics(
    mock_collect_repository, mock_collect_howfairis, assessor, sample_repository_metrics
):
    """Test assessment with FAIR compliance metrics."""
    mock_collect_repository.return_value = sample_repository_metrics

    mock_collect_howfairis.return_value = {
        "repository": True,
        "license": True,
        "registry": False,
        "citation": True,
        "checklist": False,
    }

    profile = assessor.assess(repo_url="https://github.com/owner/repo")

    assert profile is not None
    assert profile.fairness.score > 0.0
    mock_collect_howfairis.assert_called_once()


@patch("multi_modal_maturity_model.assessor.collect_publications")
def test_assess_with_citation_metrics(mock_collect_publications, assessor):
    """Test assessment with citation metrics."""
    # Return data in the format the mapper expects (flat dict with citation data)
    mock_collect_publications.return_value = {
        "citation_count": 50,
        "is_open_access": True,
    }

    profile = assessor.assess(repo_url="https://github.com/owner/repo", pmid="12345678")

    assert profile is not None
    mock_collect_publications.assert_called_once()
    # Scientific impact should be > 0 with citations
    assert profile.scientific_impact.score is not None
    assert profile.scientific_impact.score > 0.0


@patch("multi_modal_maturity_model.assessor.collect_publications")
def test_assess_with_semantic_scholar_metrics(mock_collect_publications, assessor):
    """Test assessment with Semantic Scholar DOI metrics."""
    # Return data in the format the mapper expects
    mock_collect_publications.return_value = {
        "citationCount": 75,
        "influentialCitationCount": 12,
    }

    profile = assessor.assess(
        repo_url="https://github.com/owner/repo", doi="10.1000/test-doi"
    )

    assert profile is not None
    mock_collect_publications.assert_called_once()
    assert profile.scientific_impact.score is not None
    assert profile.scientific_impact.score > 0.0


@patch("multi_modal_maturity_model.assessor.collect_publications")
def test_assess_merges_europepmc_and_semantic_scholar_metrics(
    mock_collect_publications, assessor
):
    """Test citation metrics from both providers."""
    # Return merged data in the format the mapper expects
    mock_collect_publications.return_value = {
        "citation_count": 50,
        "is_open_access": True,
        "influentialCitationCount": 12,
    }

    profile = assessor.assess(
        repo_url="https://github.com/owner/repo",
        pmid="12345678",
        doi="10.1000/test-doi",
    )

    assert profile is not None
    assert profile.scientific_impact.score is not None
    mock_collect_publications.assert_called_once()


@patch("multi_modal_maturity_model.assessor.collect_code_quality")
@patch("multi_modal_maturity_model.assessor.collect_repository")
def test_assess_skip_code_quality(
    mock_collect_repository,
    mock_collect_code_quality,
    assessor,
    sample_repository_metrics,
):
    """Test that code quality collection can be skipped."""
    mock_collect_repository.return_value = sample_repository_metrics

    profile = assessor.assess(
        repo_url="https://github.com/owner/repo",
        include_code_quality=False,  # Skip code analysis
    )

    # Code quality collection should not be called
    mock_collect_code_quality.assert_not_called()

    assert profile is not None


@patch("multi_modal_maturity_model.assessor.collect_biotools")
@patch("multi_modal_maturity_model.assessor.collect_repository")
def test_assess_with_biotools_id(
    mock_collect_repository, mock_collect_biotools, assessor, sample_repository_metrics
):
    """Test assessment with bio.tools ID."""
    mock_collect_repository.return_value = sample_repository_metrics

    mock_tool_model = Mock(spec=ToolModel)
    mock_tool_model.biotools_id = "test_tool"
    mock_tool_model.function = []
    mock_collect_biotools.return_value = mock_tool_model

    profile = assessor.assess(
        biotools_id="test_tool", repo_url="https://github.com/owner/repo"
    )

    assert profile is not None
    mock_collect_biotools.assert_called_once()


def test_get_repository_client_and_adapter(assessor):
    """Test getting the correct client and adapter for platform."""
    # Test GitHub
    client, adapter = assessor._get_repository_client_and_adapter("github")
    assert client is assessor.github_client
    assert adapter is not None

    # Test GitLab
    client, adapter = assessor._get_repository_client_and_adapter("gitlab")
    assert client is assessor.gitlab_client
    assert adapter is not None

    # Test unknown platform
    client, adapter = assessor._get_repository_client_and_adapter("unknown")
    assert client is None
    assert adapter is None
