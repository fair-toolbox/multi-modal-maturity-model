"""
Tests for the MaturityMapper class.
"""

from datetime import datetime, timedelta, timezone

import pytest

from multi_modal_maturity_model.models import (
    CodeQualityMetrics,
    EDAMItem,
    DataItem,
    Function,
    HowfairisMetrics,
    PublicationMetrics,
    RepositoryMetrics,
    ToolModel,
    Contributor,
)
from multi_modal_maturity_model import DimensionScorer, MaturityMapper


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
        last_commit_date=(datetime.now(timezone.utc) - timedelta(days=10))
        .isoformat()
        .replace("+00:00", "Z"),
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
        has_workflow_integration=True,
        has_distribution_support=True,
        has_security_policy=True,
        has_security_scanning=True,
        inverse_simpson_index=1.8,
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
    return HowfairisMetrics(
        repository=True,
        license=True,
        registry=True,
        citation=True,
        checklist=False,
    )


@pytest.fixture
def sample_publication_metrics():
    """Sample aggregated publication metrics from multiple records."""
    from multi_modal_maturity_model.models import PublicationRecord

    records = [
        PublicationRecord(
            doi="10.1234/example.doi",
            pmid="12345678",
            citation_count=50,
            fwci=1.2,
            influential_citation_count=10,
            altmetric_score=None,
            is_open_access=True,
        )
    ]

    return PublicationMetrics(
        records=records,
        publication_count=1,
        total_citation_count=50,
        total_influential_citation_count=10,
        mean_fwci=1.2,
        altmetric_score=None,
        any_open_access=True,
        all_open_access=True,
    )


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
    sample_publication_metrics,
):
    """Test mapping with all data sources available."""
    mapper = MaturityMapper()

    profile = mapper.map_to_maturity_profile(
        tool_model=sample_tool_model,
        repository_metrics=sample_repository_metrics,
        code_quality_metrics=sample_code_quality_metrics,
        fair_metrics=sample_fair_metrics,
        publication_metrics=sample_publication_metrics,
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
    assert 0.0 <= profile.overall_score.score <= 1.0

    # Check specific dimension values
    assert profile.security.score == 1.0
    assert profile.fairness.score >= 0.8  # Most FAIR criteria met


def test_map_to_maturity_profile_partial_data(sample_repository_metrics):
    """Test mapping with only repository data."""
    mapper = MaturityMapper()

    profile = mapper.map_to_maturity_profile(
        repository_metrics=sample_repository_metrics,
    )

    # Should still create a profile with some dimensions scored
    # Dimensions without data should have score 0.0
    assert profile is not None
    assert profile.security.score == 1.0
    assert profile.sustainability.score > 0.0
    assert profile.compatibility.score > 0.0
    assert profile.scientific_impact.score is None


def test_map_to_maturity_profile_no_data():
    """Test mapping with no data (all None)."""
    mapper = MaturityMapper()

    profile = mapper.map_to_maturity_profile()

    # Should create profile with all null scores
    assert profile is not None
    assert profile.overall_score.score is None
    assert profile.compatibility.score is None
    assert profile.fairness.score is None
    assert profile.maintainability.score is None
    assert profile.sustainability.score is None
    assert profile.security.score is None
    assert profile.scientific_impact.score is None


def test_map_compatibility(sample_tool_model):
    """Test compatibility dimension mapping."""
    mapper = MaturityMapper()
    score = mapper._map_compatibility(sample_tool_model, None)

    assert score.name == "Compatibility"
    assert 0.0 <= score.score <= 1.0
    assert score.score > 0.0  # Has input and output formats


def test_map_compatibility_from_repository_metadata(sample_repository_metrics):
    """Test compatibility mapping from repository metadata checks only."""
    mapper = MaturityMapper()
    score = mapper._map_compatibility(None, sample_repository_metrics)

    assert score.name == "Compatibility"
    assert score.score == 1.0
    assert score.details["workflow_support"] == 1.0
    assert score.details["distribution_support"] == 1.0


def test_calculate_edam_leaf_fraction_with_mixed_nodes():
    """Test EDAM leaf fraction calculation with mix of leaf and non-leaf nodes."""
    mapper = MaturityMapper()

    # Known leaf nodes (num_children: 0)
    leaf_formats = [
        EDAMItem(uri="http://edamontology.org/format_1197", term="InChI"),
        EDAMItem(uri="http://edamontology.org/format_1199", term="InChIKey"),
        EDAMItem(uri="http://edamontology.org/format_1215", term="pure dna"),
    ]

    # Known non-leaf nodes (num_children > 0)
    non_leaf_formats = [
        EDAMItem(
            uri="http://edamontology.org/format_2330", term="Textual format"
        ),  # 243 children
        EDAMItem(
            uri="http://edamontology.org/format_1207", term="nucleotide"
        ),  # 5 children
    ]

    # Test all leaf nodes
    result = mapper._calculate_edam_leaf_fraction(leaf_formats)
    assert result == 1.0, "All leaf nodes should return 1.0"

    # Test no leaf nodes
    result = mapper._calculate_edam_leaf_fraction(non_leaf_formats)
    assert result == 0.0, "No leaf nodes should return 0.0"

    # Test mixed: 3 leaf + 2 non-leaf = 3/5 = 0.6
    mixed_formats = leaf_formats + non_leaf_formats
    result = mapper._calculate_edam_leaf_fraction(mixed_formats)
    assert result == 0.6, f"Expected 0.6 (3/5), got {result}"

    # Test empty list
    result = mapper._calculate_edam_leaf_fraction([])
    assert result is None, "Empty list should return None"

    # Test None
    result = mapper._calculate_edam_leaf_fraction(None)
    assert result is None, "None should return None"


def test_map_compatibility_edam_leaf_validation():
    """Test compatibility mapping with EDAM leaf node validation."""
    mapper = MaturityMapper()

    # Create a ToolModel with known leaf and non-leaf formats
    tool_model = ToolModel(
        biotools_id="test_tool_edam",
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
                            # 2 leaf nodes
                            EDAMItem(
                                uri="http://edamontology.org/format_1197", term="InChI"
                            ),
                            EDAMItem(
                                uri="http://edamontology.org/format_1199",
                                term="InChIKey",
                            ),
                            # 1 non-leaf node
                            EDAMItem(
                                uri="http://edamontology.org/format_1207",
                                term="nucleotide",
                            ),
                        ],
                    )
                ],
                output=[
                    DataItem(
                        data=EDAMItem(
                            uri="http://edamontology.org/data_0857", term="Results"
                        ),
                        format=[
                            # 1 leaf node
                            EDAMItem(
                                uri="http://edamontology.org/format_1215",
                                term="pure dna",
                            ),
                            # 1 non-leaf node
                            EDAMItem(
                                uri="http://edamontology.org/format_2330",
                                term="Textual format",
                            ),
                        ],
                    )
                ],
            )
        ],
    )

    score = mapper._map_compatibility(tool_model, None)

    assert score.name == "Compatibility"
    assert score.score is not None

    # Verify the details contain the correct fractions
    # Input: 2 leaf out of 3 total = 2/3 ≈ 0.667
    # Output: 1 leaf out of 2 total = 1/2 = 0.5
    assert score.details is not None
    assert "input_formats" in score.details
    assert "output_formats" in score.details

    input_fraction = score.details["input_formats"]
    output_fraction = score.details["output_formats"]

    assert abs(input_fraction - 2 / 3) < 0.001, f"Expected ~0.667, got {input_fraction}"
    assert abs(output_fraction - 0.5) < 0.001, f"Expected 0.5, got {output_fraction}"


def test_map_compatibility_multiple_functions_aggregation():
    """Test that EDAM validation aggregates formats across multiple functions."""
    mapper = MaturityMapper()

    # Create a ToolModel with multiple functions
    tool_model = ToolModel(
        biotools_id="multi_function_tool",
        function=[
            Function(
                operation=[
                    EDAMItem(uri="http://edamontology.org/operation_0001", term="Op1")
                ],
                input=[
                    DataItem(
                        data=EDAMItem(
                            uri="http://edamontology.org/data_0001", term="Data"
                        ),
                        format=[
                            # 1 leaf node
                            EDAMItem(
                                uri="http://edamontology.org/format_1197", term="InChI"
                            ),
                        ],
                    )
                ],
                output=[
                    DataItem(
                        data=EDAMItem(
                            uri="http://edamontology.org/data_0002", term="Data"
                        ),
                        format=[
                            # 1 non-leaf node
                            EDAMItem(
                                uri="http://edamontology.org/format_2330",
                                term="Textual format",
                            ),
                        ],
                    )
                ],
            ),
            Function(
                operation=[
                    EDAMItem(uri="http://edamontology.org/operation_0002", term="Op2")
                ],
                input=[
                    DataItem(
                        data=EDAMItem(
                            uri="http://edamontology.org/data_0003", term="Data"
                        ),
                        format=[
                            # 1 non-leaf node
                            EDAMItem(
                                uri="http://edamontology.org/format_1207",
                                term="nucleotide",
                            ),
                        ],
                    )
                ],
                output=[
                    DataItem(
                        data=EDAMItem(
                            uri="http://edamontology.org/data_0004", term="Data"
                        ),
                        format=[
                            # 1 leaf node
                            EDAMItem(
                                uri="http://edamontology.org/format_1215",
                                term="pure dna",
                            ),
                        ],
                    )
                ],
            ),
        ],
    )

    score = mapper._map_compatibility(tool_model, None)

    # Aggregated across both functions:
    # Input: 1 leaf + 1 non-leaf = 1/2 = 0.5
    # Output: 1 non-leaf + 1 leaf = 1/2 = 0.5
    assert score.details["input_formats"] == 0.5
    assert score.details["output_formats"] == 0.5


def test_map_compatibility_no_formats():
    """Test compatibility mapping when tool has no format specifications."""
    mapper = MaturityMapper()

    tool_model = ToolModel(
        biotools_id="no_formats_tool",
        function=[
            Function(
                operation=[
                    EDAMItem(uri="http://edamontology.org/operation_0001", term="Op1")
                ],
                input=[
                    DataItem(
                        data=EDAMItem(
                            uri="http://edamontology.org/data_0001", term="Data"
                        ),
                        format=None,  # No formats
                    )
                ],
                output=None,  # No outputs
            )
        ],
    )

    score = mapper._map_compatibility(tool_model, None)

    # Should handle gracefully - no formats means None for fractions
    assert score.details["input_formats"] is None
    assert score.details["output_formats"] is None


def test_map_fairness(
    sample_repository_metrics, sample_fair_metrics, sample_publication_metrics
):
    """Test FAIRness dimension mapping."""
    mapper = MaturityMapper()
    score = mapper._map_fairness(
        sample_repository_metrics,
        sample_fair_metrics,
        sample_publication_metrics,
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
    assert score.details["days_since_last_commit"] == 10


def test_map_security(sample_repository_metrics):
    """Test security dimension mapping."""
    mapper = MaturityMapper()
    score = mapper._map_security(sample_repository_metrics)

    assert score.name == "Security"
    assert score.score == 1.0


def test_map_scientific_impact(sample_publication_metrics):
    """Test scientific impact dimension mapping."""
    mapper = MaturityMapper()
    score = mapper._map_scientific_impact(sample_publication_metrics)

    assert score.name == "Scientific Impact"
    assert 0.0 <= score.score <= 1.0
    assert score.score > 0.0  # Has citations
    assert score.details["total_citation_count"] == 50
    assert score.details["total_influential_citation_count"] == 10
