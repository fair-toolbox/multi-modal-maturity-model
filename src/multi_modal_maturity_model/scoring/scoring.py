"""
Calculate maturity dimensions from collected metrics.
Implements the formulas for each dimension of the maturity model.
"""

import logging
import math
from typing import Any

from ..core.models import DimensionScore, MaturityProfile

logger = logging.getLogger(__name__)


class DimensionScorer:
    """Calculate maturity dimensions from collected data."""

    @staticmethod
    def calculate_compatibility(
        input_formats: float,  # fraction of standard input formats
        output_formats: float,  # fraction of standard output formats
    ) -> DimensionScore:
        """
        Calculate Compatibility dimension.

        Formula: 0.5*[fraction of standard input formats] + 0.5*[fraction of standard output formats]

        Parameters
        ----------
        input_formats : float
            Fraction of input formats that are EDAM leaf nodes (0.0-1.0)
        output_formats : float
            Fraction of output formats that are EDAM leaf nodes (0.0-1.0)

        Returns
        -------
        DimensionScore
        """
        score = 0.5 * input_formats + 0.5 * output_formats

        return DimensionScore(
            name="Compatibility",
            score=min(1.0, max(0.0, score)),
            details={
                "input_formats": input_formats,
                "output_formats": output_formats,
            },
        )

    @staticmethod
    def calculate_fairness(
        license: bool,
        repository: bool,
        registry: bool,  # bio.tools registration
        citation: bool,
        checklist: bool,
        publication_oa: bool,
    ) -> DimensionScore:
        """
        Calculate FAIRness dimension.

        Formula: 0.2*license + 0.3*repository + 0.2*registry + 0.1*citation + 0.1*checklist + 0.1*publication_oa

        Parameters
        ----------
        license : bool
            Has explicit license
        repository : bool
            Has public code repository
        registry : bool
            Registered in bio.tools
        citation : bool
            Has citation information
        checklist : bool
            Passes FAIR checklist
        publication_oa : bool
            Associated publication is open access

        Returns
        -------
        DimensionScore
        """
        # Convert booleans to 0.0 or 1.0
        score = (
            0.2 * float(license)
            + 0.3 * float(repository)
            + 0.2 * float(registry)
            + 0.1 * float(citation)
            + 0.1 * float(checklist)
            + 0.1 * float(publication_oa)
        )

        return DimensionScore(
            name="FAIRness",
            score=min(1.0, max(0.0, score)),
            details={
                "license": license,
                "repository": repository,
                "registry": registry,
                "citation": citation,
                "checklist": checklist,
                "publication_oa": publication_oa,
            },
        )

    @staticmethod
    def calculate_maintainability(
        total_nloc: int,
        total_ccn: int,
        avg_ccn: float,
        duplicate_rate: float,
        has_old_languages: bool = False,
    ) -> DimensionScore:
        """
        Calculate Maintainability dimension.

        Based on: total NLOC, total CCN, average CCN, duplicates,
        programming language age, technology stack size.

        Heuristics:
        - Lower NLOC is better (normalized to max 10k)
        - Lower CCN is better (normalized to max 500)
        - Lower average CCN is better (normalized to max 10)
        - Lower duplicate rate is better
        - Penalty for old languages

        Parameters
        ----------
        total_nloc : int
            Total lines of code
        total_ccn : int
            Total cyclomatic complexity
        avg_ccn : float
            Average cyclomatic complexity
        duplicate_rate : float
            Fraction of duplicated code (0.0-1.0)
        has_old_languages : bool
            Whether codebase uses outdated languages

        Returns
        -------
        DimensionScore
        """
        # Normalize individual metrics (lower is better)
        nloc_score = max(0.0, 1.0 - (total_nloc / 10000.0))  # 10k NLOC as threshold
        ccn_score = max(0.0, 1.0 - (total_ccn / 500.0))  # 500 total CCN as threshold
        avg_ccn_score = max(0.0, 1.0 - (avg_ccn / 10.0))  # 10 avg CCN as threshold
        dup_score = max(0.0, 1.0 - duplicate_rate)  # 1.0 means 100% duplicates

        # Apply penalties
        lang_penalty = 0.1 if has_old_languages else 0.0

        # Weighted combination
        score = (
            0.3 * nloc_score
            + 0.2 * ccn_score
            + 0.25 * avg_ccn_score
            + 0.25 * dup_score
            - lang_penalty
        )

        return DimensionScore(
            name="Maintainability",
            score=min(1.0, max(0.0, score)),
            details={
                "total_nloc": total_nloc,
                "total_ccn": total_ccn,
                "avg_ccn": avg_ccn,
                "duplicate_rate": duplicate_rate,
                "has_old_languages": has_old_languages,
            },
        )

    @staticmethod
    def calculate_sustainability(
        avg_issue_close_time_days: float,
        num_open_issues: int,
        days_since_last_commit: int,
    ) -> DimensionScore:
        """
        Calculate Sustainability dimension.

        Based on: average time to close issues, open issues count,
        last commit date, commit frequency (Inverse Simpson Index concept).

        Heuristics:
        - Faster issue closure is better
        - Fewer open issues is better
        - Recent commits are better
        - Regular commit frequency is better

        Parameters
        ----------
        avg_issue_close_time_days : float
            Average days to close an issue
        num_open_issues : int
            Number of currently open issues
        days_since_last_commit : int

        Returns
        -------
        DimensionScore
        """
        # Normalize issue close time (lower is better, 30 days as good target)
        close_time_score = max(0.0, 1.0 - (avg_issue_close_time_days / 90.0))

        # Normalize open issues (context-dependent, but fewer is better)
        # Use logarithmic scale: 0 issues = 1.0, 100 issues = 0.0
        if num_open_issues == 0:
            open_issues_score = 1.0
        else:
            open_issues_score = max(
                0.0, 1.0 - (math.log(num_open_issues + 1) / math.log(100))
            )

        # Last commit recency (within 3 months is good)
        recent_score = max(0.0, 1.0 - (days_since_last_commit / 90.0))

        # Weighted combination
        score = 0.4 * close_time_score + 0.3 * open_issues_score + 0.2 * recent_score

        return DimensionScore(
            name="Sustainability",
            score=min(1.0, max(0.0, score)),
            details={
                "avg_issue_close_time_days": avg_issue_close_time_days,
                "num_open_issues": num_open_issues,
                "days_since_last_commit": days_since_last_commit,
            },
        )

    @staticmethod
    def calculate_security(
        default_branch_protected: bool,
    ) -> DimensionScore:
        """
        Calculate Security dimension.

        For now, based on: default branch protection status.
        Can be extended with additional metrics.

        Parameters
        ----------
        default_branch_protected : bool
            Whether the default branch is protected

        Returns
        -------
        DimensionScore
        """
        score = float(default_branch_protected)

        return DimensionScore(
            name="Security",
            score=score,
            details={
                "default_branch_protected": default_branch_protected,
            },
        )

    @staticmethod
    def calculate_scientific_impact(
        citation_count: int,
        influential_citation_count: int | None,
        max_citations_in_corpus: int,
    ) -> DimensionScore:
        """
        Calculate Scientific Impact dimension.

        Formula: log(citation_count + 0.5) / log(max_citations + 0.5)

        This normalizes citation counts logarithmically against the maximum
        in the corpus to account for scale differences across research areas.

        Parameters
        ----------
        citation_count : int
            Number of citations to the publication
        influential_citation_count : int | None
            Number of influential citations reported by Semantic Scholar
        max_citations_in_corpus : int
            Maximum citations in the reference corpus (default 1000)

        Returns
        -------
        DimensionScore
        """
        if max_citations_in_corpus <= 0:
            max_citations_in_corpus = 1000  # Default fallback

        denominator = math.log(max_citations_in_corpus + 0.5)
        citation_component = 0.0
        if denominator > 0:
            citation_component = math.log(max(citation_count, 0) + 0.5) / denominator

        influential_component = None
        if influential_citation_count is not None and denominator > 0:
            influential_component = (
                math.log(max(influential_citation_count, 0) + 0.5) / denominator
            )

        score = citation_component
        if influential_component is not None:
            # Total citations remain the primary signal, while influential
            # citations add a secondary quality-weighted contribution.
            score = (0.7 * citation_component) + (0.3 * influential_component)

        return DimensionScore(
            name="Scientific Impact",
            score=min(1.0, max(0.0, score)),
            details={
                "citation_count": citation_count,
                "influential_citation_count": influential_citation_count,
                "max_citations_in_corpus": max_citations_in_corpus,
            },
        )

    @staticmethod
    def calculate_overall_score(dimensions: list[DimensionScore]) -> float:
        """
        Calculate overall maturity score as average of all dimensions.

        Parameters
        ----------
        dimensions : list[DimensionScore]
            List of dimension scores

        Returns
        -------
        float
            Overall score (0.0-1.0)
        """
        if not dimensions:
            return 0.0
        return sum(d.score for d in dimensions) / len(dimensions)
