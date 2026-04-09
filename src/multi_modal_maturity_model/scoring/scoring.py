"""
Calculate maturity dimensions from collected metrics.
Implements the formulas for each dimension of the maturity model.
"""

import logging
import math
from typing import Any

from ..core.models import Contributor, DimensionScore

logger = logging.getLogger(__name__)

_DIMENSION_NAMES = [
    "compatibility",
    "fairness",
    "maintainability",
    "sustainability",
    "security",
    "scientific_impact",
]


class DimensionScorer:
    """Calculate maturity dimensions from collected data."""

    def _weighted_average(metrics: dict[str, tuple[float | None, float]]) -> float:
        """Return a weighted average, skipping metrics whose value is None.

        Parameters
        ----------
        metrics:
            Mapping of name → (value, weight). Entries with value=None are excluded
            and the remaining weights are renormalized automatically.
        """
        total_weight = sum(w for v, w in metrics.values() if v is not None)
        if total_weight == 0:
            return 0.0
        return sum(v * w for v, w in metrics.values() if v is not None) / total_weight

    @staticmethod
    def calculate_inverse_simpson_index(
        contributors: list[Contributor] | None,
    ) -> float | None:
        """Calculate contributor diversity from commit shares."""
        if not contributors:
            return None

        total_commits = sum(
            c.total_commits for c in contributors if c.total_commits > 0
        )
        if total_commits == 0:
            return None

        shares = [
            c.total_commits / total_commits for c in contributors if c.total_commits > 0
        ]
        hhi = sum(s**2 for s in shares)

        return (1 / hhi) if hhi else None

    @staticmethod
    def calculate_compatibility(
        input_formats: float | None = None,
        output_formats: float | None = None,
        workflow_support: float | None = None,
        distribution_support: float | None = None,
    ) -> DimensionScore:
        """
        Calculate Compatibility dimension.

        Weighted average of bio.tools I/O interoperability and repository-side
        workflow/distribution support checks, normalized over available inputs.

        Parameters
        ----------
        input_formats : float
            Fraction of input formats that are EDAM leaf nodes (0.0-1.0)
        output_formats : float
            Fraction of output formats that are EDAM leaf nodes (0.0-1.0)
        workflow_support : float | None
            Workflow integration support signal (0.0-1.0)
        distribution_support : float | None
            Runtime portability / distribution support signal (0.0-1.0)

        Returns
        -------
        DimensionScore
        """
        score = DimensionScorer._weighted_average(
            {
                "input_formats": (input_formats, 0.25),
                "output_formats": (output_formats, 0.25),
                "workflow_support": (workflow_support, 0.25),
                "distribution_support": (distribution_support, 0.25),
            }
        )

        return DimensionScore(
            name="Compatibility",
            score=min(1.0, max(0.0, score)),
            details={
                "input_formats": input_formats,
                "output_formats": output_formats,
                "workflow_support": workflow_support,
                "distribution_support": distribution_support,
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
        nloc_score = max(0.0, 1.0 - (total_nloc / 10000.0))
        ccn_score = max(0.0, 1.0 - (total_ccn / 500.0))
        avg_ccn_score = max(0.0, 1.0 - (avg_ccn / 10.0))
        dup_score = max(0.0, 1.0 - duplicate_rate)

        # Apply penalties
        lang_penalty = 0.1 if has_old_languages else 0.0

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
        days_since_last_commit: int | None,
        inverse_simpson_index: float | None = None,
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
        days_since_last_commit : int | None
        inverse_simpson_index : float | None
            Effective number of contributors based on commit-share diversity

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

        recent_score = None
        if days_since_last_commit is not None:
            # Last commit recency (within 6 months = good?)
            recent_score = max(0.0, 1.0 - (days_since_last_commit / 180.0))

        diversity_score = None
        if inverse_simpson_index is not None:
            diversity_score = max(0.0, min(1.0, 1.0 - (1.0 / inverse_simpson_index)))

        score = DimensionScorer._weighted_average(
            {
                "avg_issue_close_time_days": (close_time_score, 0.4),
                "num_open_issues": (open_issues_score, 0.3),
                "days_since_last_commit": (recent_score, 0.2),
                "inverse_simpson_index": (diversity_score, 0.1),
            }
        )

        return DimensionScore(
            name="Sustainability",
            score=min(1.0, max(0.0, score)),
            details={
                "avg_issue_close_time_days": avg_issue_close_time_days,
                "num_open_issues": num_open_issues,
                "days_since_last_commit": days_since_last_commit,
                "inverse_simpson_index": inverse_simpson_index,
            },
        )

    @staticmethod
    def calculate_security(
        default_branch_protected: bool,
        has_security_policy: bool | None = None,
        has_security_scanning: bool | None = None,
    ) -> DimensionScore:
        """
        Calculate Security dimension.

        Based on a small set of repository-level security signals.

        Parameters
        ----------
        default_branch_protected : bool
            Whether the default branch is protected
        has_security_policy : bool | None
            Whether the repository publishes a security policy or disclosure guide
        has_security_scanning : bool | None
            Whether repository files indicate automated security scanning

        Returns
        -------
        DimensionScore
        """
        signals = [float(default_branch_protected)]
        if has_security_policy is not None:
            signals.append(float(has_security_policy))
        if has_security_scanning is not None:
            signals.append(float(has_security_scanning))

        return DimensionScore(
            name="Security",
            score=sum(signals) / len(signals),
            details={
                "default_branch_protected": default_branch_protected,
                "has_security_policy": has_security_policy,
                "has_security_scanning": has_security_scanning,
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
        citation_component = (
            math.log(max(citation_count, 0) + 0.5) / denominator
            if denominator > 0
            else 0.0
        )

        influential_component = None
        if influential_citation_count is not None and denominator > 0:
            influential_component = (
                math.log(max(influential_citation_count, 0) + 0.5) / denominator
            )

        if influential_component is not None:
            score = (0.7 * citation_component) + (0.3 * influential_component)
        else:
            score = citation_component

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
    def calculate_overall_score(
        dimensions: list[DimensionScore], weights: dict[str, float] | None = None
    ) -> DimensionScore:
        """
        Calculate overall maturity score as average of all dimensions.

        Parameters
        ----------
        dimensions : list[DimensionScore]
            List of dimension scores
        weights : dict[str, float] | None
            Optional weights for each dimension. Equal weighting if None.

        Returns
        -------
        DimensionScore
        """
        if not dimensions:
            return DimensionScore(
                name="Overall", score=None, details={"note": "No dimensions available."}
            )

        if all(dim.score is None for dim in dimensions):
            return DimensionScore(
                name="Overall",
                score=None,
                details={"note": "All dimension scores are None."},
            )

        available_pairs = [
            (dim, name)
            for dim, name in zip(dimensions, _DIMENSION_NAMES)
            if dim.score is not None
        ]

        # TODO input weights and normalize
        # Return if total_weight is zero

        overall_score = sum(dim.score for dim, name in available_pairs) / len(
            available_pairs
        )

        return DimensionScore(name="Overall", score=overall_score, details={})
