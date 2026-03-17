"""
Map collected metrics to maturity dimensions.

This layer aggregates data from multiple adapters and maps them to the
appropriate dimension scoring functions.
"""

import logging
from datetime import datetime
from typing import Any

from ..core.models import (
    CodeQualityMetrics,
    DimensionScore,
    MaturityProfile,
    RepositoryMetrics,
    ToolModel,
)
from .scoring import DimensionScorer

logger = logging.getLogger(__name__)


class MaturityMapper:
    """
    Map collected data from multiple sources to maturity dimensions.

    This class orchestrates the mapping between raw collected data
    (from bio.tools, GitHub/GitLab, Lizard, howfairis, EuropePMC)
    and the dimension scoring functions.
    """

    def __init__(self, max_citations_corpus: int = 1000):
        """
        Initialize the mapper.

        Parameters
        ----------
        max_citations_corpus : int
            Maximum citations in reference corpus for normalizing
            scientific impact (default: 1000)
        """
        self.max_citations_corpus = max_citations_corpus
        self.scorer = DimensionScorer()

    def map_to_maturity_profile(
        self,
        tool_model: ToolModel | None = None,
        repository_metrics: RepositoryMetrics | None = None,
        code_quality_metrics: CodeQualityMetrics | None = None,
        fair_metrics: dict[str, Any] | None = None,
        citation_metrics: dict[str, Any] | None = None,
    ) -> MaturityProfile:
        """
        Map all collected metrics to a complete MaturityProfile.

        Parameters
        ----------
        tool_model : ToolModel | None
            From BioToolsAdapter (for compatibility dimension)
        repository_metrics : RepositoryMetrics | None
            From GitHubAdapter/GitLabAdapter (for sustainability, security)
        code_quality_metrics : CodeQualityMetrics | None
            From LizardAdapter (for maintainability)
        fair_metrics : dict[str, Any] | None
            From HowfairisCollector (for FAIRness)
        citation_metrics : dict[str, Any] | None
            From EuropePMCClient (for scientific impact)

        Returns
        -------
        MaturityProfile
            Complete maturity profile with all dimensions
        """
        # Calculate each dimension
        compatibility = self._map_compatibility(tool_model)
        fairness = self._map_fairness(
            repository_metrics, fair_metrics, citation_metrics
        )
        maintainability = self._map_maintainability(code_quality_metrics)
        sustainability = self._map_sustainability(repository_metrics)
        security = self._map_security(repository_metrics)
        scientific_impact = self._map_scientific_impact(citation_metrics)

        # Calculate overall score
        dimensions = [
            compatibility,
            fairness,
            maintainability,
            sustainability,
            security,
            scientific_impact,
        ]
        overall_score = self.scorer.calculate_overall_score(dimensions)

        return MaturityProfile(
            compatibility=compatibility,
            fairness=fairness,
            maintainability=maintainability,
            sustainability=sustainability,
            security=security,
            scientific_impact=scientific_impact,
            overall_score=overall_score,
        )

    def _map_compatibility(self, tool_model: ToolModel | None) -> DimensionScore:
        """
        Map bio.tools data to Compatibility dimension.

        Calculates fraction of input/output formats that are EDAM leaf nodes.
        """
        if not tool_model or not tool_model.function:
            logger.warning("No tool model data available for compatibility scoring")
            return DimensionScore(name="Compatibility", score=0.0)

        # Extract all input and output formats
        all_input_formats = []
        all_output_formats = []

        for function in tool_model.function:
            if function.input:
                for input_item in function.input:
                    if input_item.format:
                        all_input_formats.extend(input_item.format)

            if function.output:
                for output_item in function.output:
                    if output_item.format:
                        all_output_formats.extend(output_item.format)

        # Calculate fractions
        # TODO: Implement EDAM leaf node validation using edam_cache
        input_fraction = 1.0 if all_input_formats else 0.0
        output_fraction = 1.0 if all_output_formats else 0.0

        return self.scorer.calculate_compatibility(
            input_formats=input_fraction,
            output_formats=output_fraction,
        )

    def _map_fairness(
        self,
        repository_metrics: RepositoryMetrics | None,
        fair_metrics: dict[str, Any] | None,
        citation_metrics: dict[str, Any] | None,
    ) -> DimensionScore:
        """
        Map data from multiple sources to FAIRness dimension.

        Combines data from:
        - GitHub/GitLab (license, repository)
        - howfairis (all FAIR indicators)
        - EuropePMC (open access status)
        """
        # Default values
        license_val = False
        repository_val = False
        registry_val = False
        citation_val = False
        checklist_val = False
        publication_oa = False

        # Get data from howfairis (primary source for FAIR)
        if fair_metrics:
            license_val = fair_metrics.get("license", False)
            repository_val = fair_metrics.get("repository", False)
            registry_val = fair_metrics.get("registry", False)
            citation_val = fair_metrics.get("citation", False)
            checklist_val = fair_metrics.get("checklist", False)

        # Fallback to repository metrics for license if available
        if repository_metrics and not license_val:
            license_val = repository_metrics.has_license

        # Get open access status from citation metrics
        if citation_metrics:
            publication_oa = citation_metrics.get("is_open_access", False)

        return self.scorer.calculate_fairness(
            license=license_val,
            repository=repository_val,
            registry=registry_val,
            citation=citation_val,
            checklist=checklist_val,
            publication_oa=publication_oa,
        )

    def _map_maintainability(
        self,
        code_quality_metrics: CodeQualityMetrics | None,
    ) -> DimensionScore:
        """
        Map code quality data to Maintainability dimension.

        Uses Lizard metrics.
        """
        if not code_quality_metrics:
            logger.warning("No code quality metrics available for maintainability")
            return DimensionScore(name="Maintainability", score=0.0)

        # TODO: Detect old/outdated languages
        has_old_languages = False

        return self.scorer.calculate_maintainability(
            total_nloc=code_quality_metrics.total_nloc or 0,
            total_ccn=code_quality_metrics.total_ccn or 0,
            avg_ccn=code_quality_metrics.avg_ccn or 0.0,
            duplicate_rate=code_quality_metrics.duplicate_rate or 0.0,
            has_old_languages=has_old_languages,
        )

    def _map_sustainability(
        self, repository_metrics: RepositoryMetrics | None
    ) -> DimensionScore:
        """
        Map repository activity data to Sustainability dimension.
        """
        if not repository_metrics:
            logger.warning("No repository metrics available for sustainability")
            return DimensionScore(name="Sustainability", score=0.0)

        # Calculate days since last commit
        # TODO: This requires commit date data - add to RepositoryMetrics
        days_since_last_commit = 0  # Placeholder

        return self.scorer.calculate_sustainability(
            avg_issue_close_time_days=repository_metrics.avg_time_to_close_days or 90.0,
            num_open_issues=repository_metrics.open_issues,
            days_since_last_commit=days_since_last_commit,
        )

    def _map_security(
        self, repository_metrics: RepositoryMetrics | None
    ) -> DimensionScore:
        """
        Map repository security settings to Security dimension.
        """
        if not repository_metrics:
            logger.warning("No repository metrics available for security")
            return DimensionScore(name="Security", score=0.0)

        return self.scorer.calculate_security(
            default_branch_protected=repository_metrics.default_branch_is_protected
            or False
        )

    def _map_scientific_impact(
        self, citation_metrics: dict[str, Any] | None
    ) -> DimensionScore:
        """
        Map citation data to Scientific Impact dimension.
        """
        if not citation_metrics:
            logger.warning("No citation metrics available for scientific impact")
            return DimensionScore(name="Scientific Impact", score=0.0)

        citation_count = citation_metrics.get("citation_count", 0)

        return self.scorer.calculate_scientific_impact(
            citation_count=citation_count,
            max_citations_in_corpus=self.max_citations_corpus,
        )
