"""
Map collected metrics to maturity dimensions.

This layer aggregates data from multiple clients, adapters and analyzers and maps them to the appropriate dimension scoring functions.
"""

import logging

from .edam import EDAMCache

from .models import (
    CodeQualityMetrics,
    DimensionScore,
    EDAMItem,
    HowfairisMetrics,
    MaturityProfile,
    PublicationMetrics,
    RepositoryMetrics,
    ToolModel,
)
from .scoring import DimensionScorer
from .utils import calculate_days_since_last_commit


logger = logging.getLogger(__name__)


class MaturityMapper:
    """
    Map collected metrics from sources to maturity dimensions.
    """

    def __init__(
        self,
        max_citations_corpus: int = 1000,
        weights: dict[str, dict[str, float]] | None = None,
    ):
        """
        Initialize the mapper.

        Parameters
        ----------
        max_citations_corpus : int
            Maximum citations in reference corpus for normalizing
            scientific impact (default: 1000)
        weights : dict[str, dict[str, float]] | None
            Custom weights for dimensions and overall score.
            If None, uses defaults from weights.py.
        """
        self.max_citations_corpus = max_citations_corpus
        self.scorer = DimensionScorer(weights=weights)
        self.edam_cache = EDAMCache()

    def map_to_maturity_profile(
        self,
        tool_model: ToolModel | None = None,
        repository_metrics: RepositoryMetrics | None = None,
        code_quality_metrics: CodeQualityMetrics | None = None,
        fair_metrics: HowfairisMetrics | None = None,
        publication_metrics: PublicationMetrics | None = None,
    ) -> MaturityProfile:
        """
        Map all collected metrics to a complete MaturityProfile.

        Parameters
        ----------
        tool_model : ToolModel | None
        repository_metrics : RepositoryMetrics | None
        code_quality_metrics : CodeQualityMetrics | None
        fair_metrics : HowfairisMetrics | None
        publication_metrics : PublicationMetrics | None

        Returns
        -------
        MaturityProfile
            Complete maturity profile with all dimensions
        """
        compatibility = self._map_compatibility(tool_model, repository_metrics)
        fairness = self._map_fairness(
            repository_metrics, fair_metrics, publication_metrics
        )
        maintainability = self._map_maintainability(code_quality_metrics)
        sustainability = self._map_sustainability(repository_metrics)
        security = self._map_security(repository_metrics)
        scientific_impact = self._map_scientific_impact(publication_metrics)

        logger.info("Mapping complete. Calculating overall score...")

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

    def _calculate_edam_leaf_fraction(self, formats: list[EDAMItem]) -> float | None:
        if not formats:
            return None

        leaf_count = sum(1 for fmt in formats if self.edam_cache.is_leaf_node(fmt.uri))
        return leaf_count / len(formats)

    def _map_compatibility(
        self,
        tool_model: ToolModel | None,
        repository_metrics: RepositoryMetrics | None,
    ) -> DimensionScore:
        """
        Map bio.tools data to Compatibility dimension.

        Calculates fraction of input/output formats that are EDAM leaf nodes.
        """
        if not tool_model and not repository_metrics:
            logger.warning("No data available for compatibility")
            return DimensionScore(name="Compatibility", score=None)

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

            input_fraction = self._calculate_edam_leaf_fraction(all_input_formats)
            output_fraction = self._calculate_edam_leaf_fraction(all_output_formats)

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
        fair_metrics: HowfairisMetrics | None,
        publication_metrics: PublicationMetrics | None,
    ) -> DimensionScore:
        """
        Map data from multiple sources to FAIRness dimension.

        Combines data from:
        - GitHub/GitLab (license, repository)
        - howfairis (all FAIR indicators)
        - EuropePMC (open access status)
        """
        if not fair_metrics:
            logger.warning("No fair metrics available for FAIRness")
            return DimensionScore(name="FAIRness", score=None)

        license_val = (
            fair_metrics.license
            if fair_metrics
            else repository_metrics.has_license if repository_metrics else False
        )
        values = {
            "license": license_val,
            "repository": fair_metrics.repository,
            "registry": fair_metrics.registry,
            "citation": fair_metrics.citation,
            "checklist": fair_metrics.checklist,
            "publication_oa": (
                publication_metrics.is_open_access if publication_metrics else None
            ),
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

        days_since_last_commit = calculate_days_since_last_commit(
            repository_metrics.last_commit_date
        )

        return self.scorer.calculate_sustainability(
            avg_issue_close_time_days=repository_metrics.avg_time_to_close_days,
            num_open_issues=repository_metrics.open_issues,
            days_since_last_commit=days_since_last_commit,
            inverse_simpson_index=repository_metrics.inverse_simpson_index,
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
        self, publication_metrics: PublicationMetrics | None
    ) -> DimensionScore:
        """
        Map citation data to Scientific Impact dimension.
        """
        if not publication_metrics:
            logger.warning("No publication metrics available for scientific impact")
            return DimensionScore(name="Scientific Impact", score=None)

        return self.scorer.calculate_scientific_impact(
            citation_count=publication_metrics.citation_count or 0,
            influential_citation_count=publication_metrics.influential_citation_count
            or None,
            max_citations_in_corpus=self.max_citations_corpus,
        )
