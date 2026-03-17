"""
Tests for the MaturityMapper class.
"""

import pytest

from multi_modal_maturity_model.core.models import (
    CodeQualityMetrics,
    EDAMItem,
    DataItem,
    Function,
    RepositoryMetrics,
    ToolModel,
    Contributor,
)
from multi_modal_maturity_model.scoring import MaturityMapper


@pytest.fixture
def sample_tool_model():
    """Sample ToolModel with input/output formats."""
    return ToolModel(
        biotools_id="test_tool",
        function=[
            Function(
                operation=[
                    EDAMItem(
                        uri="http://edamontology.org/operation_0004", term="Operation"
                    )
                ],
                input=[
                    DataItem(
                        data=EDAMItem(
                            uri="http://edamontology.org/data_0001", term="Data"
                        ),
                        format=[
                            EDAMItem(
                                uri="http://edamontology.org/format_1929", term="FASTA"
                            ),
                            EDAMItem(
                                uri="http://edamontology.org/format_1936",
                                term="GenBank",
                            ),
                        ],
                    )
                ],
                output=[
                    DataItem(
                        data=EDAMItem(
                            uri="http://edamontology.org/data_0857",
                            term="Sequence search results",
                        ),
                        format=[
                            EDAMItem(
                                uri="http://edamontology.org/format_1333",
                                term="BLAST results",
                            ),
                        ],
                    )
                ],
            )
        ],
    )


@pytest.fixture
def sample_repository_metrics():
    """Sample RepositoryMetrics."""
    return RepositoryMetrics(
        platform="github",
        url="https://github.com/test/repo",
        repo="test/repo",
        default_branch="main",
        stars=100,
        forks=20,
        open_issues=5,
        avg_time_to_close_days=10.5,
        default_branch_is_protected=True,
        languages=["Python", "JavaScript"],
        has_license=True,
        contributors=[
            Contributor(login="user1", total_commits=50),
            Contributor(login="user2", total_commits=30),
        ],
    )


@pytest.fixture
def sample_code_quality_metrics():
    """Sample CodeQualityMetrics."""
    return CodeQualityMetrics(
        total_nloc=5000,
        total_ccn=200,
        avg_ccn=5.0,
        duplicate_rate=0.1,
    )


@pytest.fixture
def sample_fair_metrics():
    """Sample FAIR metrics from howfairis."""
    return {
        "repository": True,
        "license": True,
        "registry": True,
        "citation": True,
        "checklist": False,
    }


@pytest.fixture
def sample_citation_metrics():
    """Sample citation metrics from EuropePMC."""
    return {
        "citation_count": 50,
        "is_open_access": True,
    }


def test_mapper_initialization():
    """Test MaturityMapper initialization."""
    mapper = MaturityMapper(max_citations_corpus=2000)
    assert mapper.max_citations_corpus == 2000
    assert mapper.scorer is not None


def test_map_to_maturity_profile_all_data(
    sample_tool_model,
    sample_repository_metrics,
    sample_code_quality_metrics,
    sample_fair_metrics,
    sample_citation_metrics,
):
    """Test mapping with all data sources available."""
    mapper = MaturityMapper()

    profile = mapper.map_to_maturity_profile(
        tool_model=sample_tool_model,
        repository_metrics=sample_repository_metrics,
        code_quality_metrics=sample_code_quality_metrics,
        fair_metrics=sample_fair_metrics,
        citation_metrics=sample_citation_metrics,
    )

    # Check that profile is created
    assert profile is not None

    # Check that all dimensions have scores between 0 and 1
    assert 0.0 <= profile.compatibility.score <= 1.0
    assert 0.0 <= profile.fairness.score <= 1.0
    assert 0.0 <= profile.maintainability.score <= 1.0
    assert 0.0 <= profile.sustainability.score <= 1.0
    assert 0.0 <= profile.security.score <= 1.0
    assert 0.0 <= profile.scientific_impact.score <= 1.0
    assert 0.0 <= profile.overall_score <= 1.0

    # Check specific dimension values
    assert profile.security.score == 1.0  # Branch is protected
    assert profile.fairness.score >= 0.8  # Most FAIR criteria met


def test_map_to_maturity_profile_partial_data(sample_repository_metrics):
    """Test mapping with only repository data."""
    mapper = MaturityMapper()

    profile = mapper.map_to_maturity_profile(
        repository_metrics=sample_repository_metrics,
    )

    # Should still create a profile with some dimensions scored
    assert profile is not None
    assert profile.security.score == 1.0
    assert profile.sustainability.score > 0.0

    # Dimensions without data should have score 0.0
    assert profile.compatibility.score == 0.0
    assert profile.scientific_impact.score == 0.0


def test_map_to_maturity_profile_no_data():
    """Test mapping with no data (all None)."""
    mapper = MaturityMapper()

    profile = mapper.map_to_maturity_profile()

    # Should create profile with all zero scores
    assert profile is not None
    assert profile.overall_score == 0.0
    assert profile.compatibility.score == 0.0
    assert profile.fairness.score == 0.0
    assert profile.maintainability.score == 0.0
    assert profile.sustainability.score == 0.0
    assert profile.security.score == 0.0
    assert profile.scientific_impact.score == 0.0


def test_map_compatibility(sample_tool_model):
    """Test compatibility dimension mapping."""
    mapper = MaturityMapper()
    score = mapper._map_compatibility(sample_tool_model)

    assert score.name == "Compatibility"
    assert 0.0 <= score.score <= 1.0
    assert score.score > 0.0  # Has input and output formats


def test_map_fairness(
    sample_repository_metrics, sample_fair_metrics, sample_citation_metrics
):
    """Test FAIRness dimension mapping."""
    mapper = MaturityMapper()
    score = mapper._map_fairness(
        sample_repository_metrics,
        sample_fair_metrics,
        sample_citation_metrics,
    )

    assert score.name == "FAIRness"
    assert 0.0 <= score.score <= 1.0
    assert score.score >= 0.8  # Most criteria met


def test_map_maintainability(sample_code_quality_metrics, sample_repository_metrics):
    """Test maintainability dimension mapping."""
    mapper = MaturityMapper()
    score = mapper._map_maintainability(
        sample_code_quality_metrics,
    )

    assert score.name == "Maintainability"
    assert 0.0 <= score.score <= 1.0


def test_map_sustainability(sample_repository_metrics):
    """Test sustainability dimension mapping."""
    mapper = MaturityMapper()
    score = mapper._map_sustainability(sample_repository_metrics)

    assert score.name == "Sustainability"
    assert 0.0 <= score.score <= 1.0


def test_map_security(sample_repository_metrics):
    """Test security dimension mapping."""
    mapper = MaturityMapper()
    score = mapper._map_security(sample_repository_metrics)

    assert score.name == "Security"
    assert score.score == 1.0  # Branch is protected


def test_map_scientific_impact(sample_citation_metrics):
    """Test scientific impact dimension mapping."""
    mapper = MaturityMapper()
    score = mapper._map_scientific_impact(sample_citation_metrics)

    assert score.name == "Scientific Impact"
    assert 0.0 <= score.score <= 1.0
    assert score.score > 0.0  # Has citations
