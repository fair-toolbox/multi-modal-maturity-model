"""Tests for extraction module."""

import pytest
from multi_modal_maturity_model.extraction import (
    _extract_direct,
    _extract_existence_check,
    _extract_pattern_match,
    _extract_publication,
    calculate_days_since_last_commit,
    calculate_avg_time_to_close,
    calculate_inverse_simpson_index,
    extract_metric,
)


class TestDirectExtraction:
    """Test direct value extraction."""

    def test_extract_direct_simple_path(self):
        """Test extracting value from simple path."""
        source_cfg = {"path": "repository.stargazers_count"}
        raw_data = {"repository": {"stargazers_count": 42}}

        result = _extract_direct(source_cfg, raw_data)
        assert result == 42

    def test_extract_direct_nested_path(self):
        """Test extracting value from nested path."""
        source_cfg = {"path": "repository.owner.login"}
        raw_data = {"repository": {"owner": {"login": "testuser"}}}

        result = _extract_direct(source_cfg, raw_data)
        assert result == "testuser"

    def test_extract_direct_missing_path(self):
        """Test extracting from non-existent path returns None."""
        source_cfg = {"path": "nonexistent.path"}
        raw_data = {"repository": {"stargazers_count": 42}}

        result = _extract_direct(source_cfg, raw_data)
        assert result is None


class TestExistenceCheck:
    """Test existence checking."""

    def test_existence_check_true(self):
        """Test existence check returns True for existing value."""
        source_cfg = {"path": "biotoolsID"}
        raw_data = {"biotoolsID": "test_tool"}

        result = _extract_existence_check(source_cfg, raw_data)
        assert result is True

    def test_existence_check_false_none(self):
        """Test existence check returns False for None."""
        source_cfg = {"path": "biotoolsID"}
        raw_data = {"biotoolsID": None}

        result = _extract_existence_check(source_cfg, raw_data)
        assert result is False

    def test_existence_check_false_empty_string(self):
        """Test existence check returns False for empty string."""
        source_cfg = {"path": "biotoolsID"}
        raw_data = {"biotoolsID": ""}

        result = _extract_existence_check(source_cfg, raw_data)
        assert result is False

    def test_existence_check_false_empty_list(self):
        """Test existence check returns False for empty list."""
        source_cfg = {"path": "items"}
        raw_data = {"items": []}

        result = _extract_existence_check(source_cfg, raw_data)
        assert result is False


class TestPatternMatch:
    """Test pattern matching."""

    def test_pattern_match_simple(self):
        """Test simple pattern match."""
        source_cfg = {"pattern_group": "workflow_files", "path": "contents"}
        raw_data = {"contents": [{"name": "workflow.cwl"}, {"name": "script.py"}]}
        patterns = {"workflow_files": ["*.cwl", "*.wdl"]}

        result = _extract_pattern_match(source_cfg, raw_data, patterns)
        assert result is True

    def test_pattern_match_no_match(self):
        """Test pattern match returns False when no match."""
        source_cfg = {"pattern_group": "workflow_files", "path": "contents"}
        raw_data = {"contents": [{"name": "script.py"}, {"name": "README.md"}]}
        patterns = {"workflow_files": ["*.cwl", "*.wdl"]}

        result = _extract_pattern_match(source_cfg, raw_data, patterns)
        assert result is False

    def test_pattern_match_nested_patterns(self):
        """Test pattern match with nested pattern structure."""
        source_cfg = {"pattern_group": "workflow_files", "path": "contents"}
        raw_data = {"contents": [{"name": "Dockerfile"}]}
        patterns = {
            "workflow_files": {
                "cwl": ["*.cwl"],
                "docker": ["Dockerfile"],
            }
        }

        result = _extract_pattern_match(source_cfg, raw_data, patterns)
        assert result is True

    def test_pattern_match_case_insensitive(self):
        """Test pattern match is case-insensitive."""
        source_cfg = {"pattern_group": "workflow_files", "path": "contents"}
        raw_data = {"contents": [{"name": "WORKFLOW.CWL"}]}
        patterns = {"workflow_files": ["*.cwl"]}

        result = _extract_pattern_match(source_cfg, raw_data, patterns)
        assert result is True


class TestPublicationExtraction:
    """Test publication aggregation."""

    def test_publication_sum(self):
        """Test publication aggregation with sum."""
        source_cfg = {"path": "cited_by_count"}
        papers = [
            {"cited_by_count": 10},
            {"cited_by_count": 20},
            {"cited_by_count": 30},
        ]

        result = _extract_publication(source_cfg, papers, "sum")
        assert result == 60

    def test_publication_mean(self):
        """Test publication aggregation with mean."""
        source_cfg = {"path": "cited_by_count"}
        papers = [
            {"cited_by_count": 10},
            {"cited_by_count": 20},
            {"cited_by_count": 30},
        ]

        result = _extract_publication(source_cfg, papers, "mean")
        assert result == 20

    def test_publication_max(self):
        """Test publication aggregation with max."""
        source_cfg = {"path": "fwci"}
        papers = [
            {"fwci": 1.2},
            {"fwci": 2.5},
            {"fwci": 1.8},
        ]

        result = _extract_publication(source_cfg, papers, "max")
        assert result == 2.5

    def test_publication_any(self):
        """Test publication aggregation with any."""
        source_cfg = {"path": "open_access.is_oa"}
        papers = [
            {"open_access": {"is_oa": False}},
            {"open_access": {"is_oa": True}},
            {"open_access": {"is_oa": False}},
        ]

        result = _extract_publication(source_cfg, papers, "any")
        assert result is True


class TestCalculatedFunctions:
    """Test calculated metric functions."""

    def test_calculate_days_since_last_commit(self):
        """Test days since last commit calculation."""
        source_cfg = {"path": "repository.pushed_at"}
        raw_data = {"repository": {"pushed_at": "2026-01-01T00:00:00Z"}}

        result = calculate_days_since_last_commit(source_cfg, raw_data)
        # Result should be a positive integer (days since Jan 1, 2026)
        assert isinstance(result, int)
        assert result >= 0

    def test_calculate_avg_time_to_close(self):
        """Test average issue close time calculation."""
        source_cfg = {"path": "closed_issues"}
        raw_data = {
            "closed_issues": [
                {
                    "created_at": "2026-01-01T00:00:00Z",
                    "closed_at": "2026-01-11T00:00:00Z",  # 10 days
                },
                {
                    "created_at": "2026-01-01T00:00:00Z",
                    "closed_at": "2026-01-21T00:00:00Z",  # 20 days
                },
            ]
        }

        result = calculate_avg_time_to_close(source_cfg, raw_data)
        assert result == 15.0  # Average of 10 and 20

    def test_calculate_inverse_simpson_index(self):
        """Test inverse Simpson index calculation."""
        source_cfg = {
            "path": "contributors",
            "params": {"login_key": "login", "commits_key": "contributions"},
        }
        raw_data = {
            "contributors": [
                {"login": "user1", "contributions": 50},
                {"login": "user2", "contributions": 30},
                {"login": "user3", "contributions": 20},
            ]
        }

        result = calculate_inverse_simpson_index(source_cfg, raw_data)
        # Result should be > 1 (diversity index)
        assert isinstance(result, float)
        assert result > 1.0


class TestExtractMetric:
    """Test main extract_metric function."""

    def test_extract_metric_direct(self):
        """Test extracting metric with direct method."""
        metric_cfg = {
            "extraction": {
                "method": "direct",
                "sources": {
                    "github": {"path": "repository.stargazers_count"},
                },
            }
        }
        results = {"github": {"repository": {"stargazers_count": 42}}}

        result = extract_metric("star_count", metric_cfg, results)
        assert result == {"github": 42}

    def test_extract_metric_multiple_sources(self):
        """Test extracting metric from multiple sources."""
        metric_cfg = {
            "extraction": {
                "method": "direct",
                "sources": {
                    "github": {"path": "repository.stargazers_count"},
                    "gitlab": {"path": "repository.star_count"},
                },
            }
        }
        results = {
            "github": {"repository": {"stargazers_count": 42}},
            "gitlab": {"repository": {"star_count": 35}},
        }

        result = extract_metric("star_count", metric_cfg, results)
        assert result == {"github": 42, "gitlab": 35}

    def test_extract_metric_existence_check(self):
        """Test extracting metric with existence check."""
        metric_cfg = {
            "extraction": {
                "method": "existence_check",
                "sources": {
                    "biotools": {"path": "biotoolsID"},
                },
            }
        }
        results = {"biotools": {"biotoolsID": "test_tool"}}

        result = extract_metric("biotools_registry", metric_cfg, results)
        assert result == {"biotools": True}
