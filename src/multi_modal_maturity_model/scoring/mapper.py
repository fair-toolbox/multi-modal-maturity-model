"""
Map collected metrics to maturity dimensions.

This layer aggregates data from multiple adapters and collectors and maps them to the
appropriate dimension scoring functions.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from ..adapters.adapters_utils import parse_iso_datetime
from ..models import (
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
        compatibility = self._map_compatibility(tool_model, repository_metrics)
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

    def _map_compatibility(
        self,
        tool_model: ToolModel | None,
        repository_metrics: RepositoryMetrics | None,
    ) -> DimensionScore:
        """
        Map bio.tools data to Compatibility dimension.

        Calculates fraction of input/output formats that are EDAM leaf nodes.
        """
        input_fraction = None
        output_fraction = None

        if tool_model and tool_model.function:
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

            # TODO: Implement EDAM leaf node validation using edam_cache
            input_fraction = 1.0 if all_input_formats else 0.0
            output_fraction = 1.0 if all_output_formats else 0.0
        else:
            logger.warning(
                "No tool model data available for bio.tools compatibility scoring"
            )

        workflow_support = None
        distribution_support = None
        if repository_metrics:
            if repository_metrics.has_workflow_integration is not None:
                workflow_support = float(repository_metrics.has_workflow_integration)
            if repository_metrics.has_distribution_support is not None:
                distribution_support = float(
                    repository_metrics.has_distribution_support
                )

        return self.scorer.calculate_compatibility(
            input_formats=input_fraction,
            output_formats=output_fraction,
            workflow_support=workflow_support,
            distribution_support=distribution_support,
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
        fair_metrics = fair_metrics or {}
        citation_metrics = citation_metrics or {}

        license_val = fair_metrics.get("license") or (
            repository_metrics.has_license if repository_metrics else False
        )
        values = {
            "license": license_val,
            "repository": fair_metrics.get("repository", False),
            "registry": fair_metrics.get("registry", False),
            "citation": fair_metrics.get("citation", False),
            "checklist": fair_metrics.get("checklist", False),
            "publication_oa": citation_metrics.get("is_open_access", False),
        }
        return self.scorer.calculate_fairness(**values)

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
            return DimensionScore(name="Maintainability", score=None)

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
            return DimensionScore(name="Sustainability", score=None)

        days_since_last_commit = None
        if repository_metrics.last_commit_date:
            try:
                last_commit_date = parse_iso_datetime(
                    repository_metrics.last_commit_date
                )
                now = datetime.now(last_commit_date.tzinfo or timezone.utc)
                days_since_last_commit = max(0, (now - last_commit_date).days)
            except ValueError as error:
                logger.debug(f"Could not parse last commit date: {error}")

        inverse_simpson_index = self.scorer.calculate_inverse_simpson_index(
            repository_metrics.contributors
        )

        return self.scorer.calculate_sustainability(
            avg_issue_close_time_days=repository_metrics.avg_time_to_close_days or 90.0,
            num_open_issues=repository_metrics.open_issues,
            days_since_last_commit=days_since_last_commit,
            inverse_simpson_index=inverse_simpson_index,
        )

    def _map_security(
        self, repository_metrics: RepositoryMetrics | None
    ) -> DimensionScore:
        """
        Map repository security settings to Security dimension.
        """
        if not repository_metrics:
            logger.warning("No repository metrics available for security")
            return DimensionScore(name="Security", score=None)

        return self.scorer.calculate_security(
            default_branch_protected=repository_metrics.default_branch_is_protected
            or False,
            has_security_policy=repository_metrics.has_security_policy,
            has_security_scanning=repository_metrics.has_security_scanning,
        )

    def _map_scientific_impact(
        self, citation_metrics: dict[str, Any] | None
    ) -> DimensionScore:
        """
        Map citation data to Scientific Impact dimension.
        """
        if not citation_metrics:
            logger.warning("No citation metrics available for scientific impact")
            return DimensionScore(name="Scientific Impact", score=None)

        citation_count = citation_metrics.get(
            "citation_count",
            citation_metrics.get("citationCount", 0),
        )
        influential_citation_count = citation_metrics.get(
            "influential_citation_count",
            citation_metrics.get("influentialCitationCount"),
        )

        return self.scorer.calculate_scientific_impact(
            citation_count=citation_count,
            influential_citation_count=influential_citation_count,
            max_citations_in_corpus=self.max_citations_corpus,
        )
