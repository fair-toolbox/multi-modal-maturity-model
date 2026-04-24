"""
Calculate maturity dimensions from collected metrics.
Implements the formulas for each dimension of the maturity model.
"""

import logging
import math

from .models import DimensionScore
from .weights import build_weights

logger = logging.getLogger(__name__)

# Normalisation ceilings
_MAX_NLOC = 10_000
_MAX_CCN = 500
_MAX_AVG_CCN = 10.0
_ISSUE_CLOSE_TIME_CEILING_DAYS = 90.0
_RECENT_COMMIT_WINDOW_DAYS = 180.0

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

    def __init__(self, weights: dict[str, dict[str, float]] | None = None):
        """
        Initialize scorer with optional custom weights.

        Parameters
        ----------
        weights : dict[str, dict[str, float]] | None
            Custom weights configuration. If None, uses defaults.
            Example:
            {
                "compatibility": {"input_formats": 0.25, "output_formats": 0.25, ...},
                "overall": {"compatibility": 0.2, "fairness": 0.2, ...},
            }

        Raises
        ------
        ValueError
            If weights dict is invalid (via validate_weights).
        """
        self._weights = build_weights(weights)

    def calculate_compatibility(
        self,
        input_formats: float | None = None,
        output_formats: float | None = None,
        workflow_support: float | None = None,
        distribution_support: float | None = None,
    ) -> DimensionScore:
        """
        Calculate Compatibility dimension.

        Weighted average of bio.tools I/O interoperability and repository-side
        workflow/distribution support checks, normalised over available inputs.

        Parameters
        ----------
        input_formats : float | None
            Fraction of input formats that are EDAM leaf nodes (0.0–1.0)
        output_formats : float | None
            Fraction of output formats that are EDAM leaf nodes (0.0–1.0)
        workflow_support : float | None
            Workflow integration support signal (0.0–1.0)
        distribution_support : float | None
            Runtime portability / distribution support signal (0.0–1.0)
        """
        w = self._weights["compatibility"]
        score = _weighted_average(
            {
                "input_formats": (input_formats, w["input_formats"]),
                "output_formats": (output_formats, w["output_formats"]),
                "workflow_support": (workflow_support, w["workflow_support"]),
                "distribution_support": (
                    distribution_support,
                    w["distribution_support"],
                ),
            }
        )
        return DimensionScore(
            name="Compatibility",
            score=_clamp(score),
            details={
                "input_formats": input_formats,
                "output_formats": output_formats,
                "workflow_support": workflow_support,
                "distribution_support": distribution_support,
            },
        )

    def calculate_fairness(
        self,
        license: bool,
        repository: bool,
        registry: bool,
        citation: bool,
        checklist: bool,
        publication_oa: bool | None = None,
    ) -> DimensionScore:
        """
        Calculate FAIRness dimension.

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
        publication_oa : bool | None
            Associated publication is open access (None treated as False)
        """
        w = self._weights["fairness"]
        oa = publication_oa if publication_oa is not None else False
        score = (
            w["license"] * float(license)
            + w["repository"] * float(repository)
            + w["registry"] * float(registry)
            + w["citation"] * float(citation)
            + w["checklist"] * float(checklist)
            + w["publication_oa"] * float(oa)
        )
        return DimensionScore(
            name="FAIRness",
            score=_clamp(score),
            details={
                "license": license,
                "repository": repository,
                "registry": registry,
                "citation": citation,
                "checklist": checklist,
                "publication_oa": publication_oa,
            },
        )

    def calculate_maintainability(
        self,
        total_nloc: int,
        total_ccn: int,
        avg_ccn: float,
        duplicate_rate: float,
        has_old_languages: bool = False,
    ) -> DimensionScore:
        """
        Calculate Maintainability dimension.

        Lower NLOC, CCN, avg CCN, and duplicate rate each produce a higher score.
        An optional penalty applies when the codebase uses outdated languages.

        Parameters
        ----------
        total_nloc : int
            Total lines of code
        total_ccn : int
            Total cyclomatic complexity
        avg_ccn : float
            Average cyclomatic complexity per function
        duplicate_rate : float
            Fraction of duplicated code (0.0–1.0)
        has_old_languages : bool
            Whether the codebase uses outdated languages
        """
        w = self._weights["maintainability"]

        nloc_score = max(0.0, 1.0 - (total_nloc / _MAX_NLOC))
        ccn_score = max(0.0, 1.0 - (total_ccn / _MAX_CCN))
        avg_ccn_score = max(0.0, 1.0 - (avg_ccn / _MAX_AVG_CCN))
        dup_score = max(0.0, 1.0 - duplicate_rate)
        lang_penalty = 0.1 if has_old_languages else 0.0

        score = (
            w["nloc"] * nloc_score
            + w["ccn"] * ccn_score
            + w["avg_ccn"] * avg_ccn_score
            + w["duplicate_rate"] * dup_score
            - lang_penalty
        )
        return DimensionScore(
            name="Maintainability",
            score=_clamp(score),
            details={
                "total_nloc": total_nloc,
                "total_ccn": total_ccn,
                "avg_ccn": avg_ccn,
                "duplicate_rate": duplicate_rate,
                "has_old_languages": has_old_languages,
            },
        )

    def calculate_sustainability(
        self,
        avg_issue_close_time_days: float | None,
        num_open_issues: int,
        days_since_last_commit: int | None,
        inverse_simpson_index: float | None = None,
    ) -> DimensionScore:
        """
        Calculate Sustainability dimension.

        Heuristics: faster issue closure, fewer open issues, recent commits,
        and diverse contributor activity all increase the score.

        Parameters
        ----------
        avg_issue_close_time_days : float | None
            Average days to close an issue
        num_open_issues : int
            Number of currently open issues
        days_since_last_commit : int | None
            Days since the most recent commit
        inverse_simpson_index : float | None
            Effective number of contributors based on commit-share diversity
        """
        w = self._weights["sustainability"]

        close_time_score = (
            max(0.0, 1.0 - (avg_issue_close_time_days / _ISSUE_CLOSE_TIME_CEILING_DAYS))
            if avg_issue_close_time_days is not None
            else None
        )

        open_issues_score = (
            1.0
            if num_open_issues == 0
            else max(0.0, 1.0 - (math.log(num_open_issues + 1) / math.log(100)))
        )

        recent_score = (
            max(0.0, 1.0 - (days_since_last_commit / _RECENT_COMMIT_WINDOW_DAYS))
            if days_since_last_commit is not None
            else None
        )

        diversity_score = (
            max(0.0, min(1.0, 1.0 - (1.0 / inverse_simpson_index)))
            if inverse_simpson_index is not None
            else None
        )

        score = _weighted_average(
            {
                "avg_issue_close_time_days": (
                    close_time_score,
                    w["avg_issue_close_time_days"],
                ),
                "num_open_issues": (open_issues_score, w["num_open_issues"]),
                "days_since_last_commit": (recent_score, w["days_since_last_commit"]),
                "inverse_simpson_index": (diversity_score, w["inverse_simpson_index"]),
            }
        )
        return DimensionScore(
            name="Sustainability",
            score=_clamp(score),
            details={
                "avg_issue_close_time_days": avg_issue_close_time_days,
                "num_open_issues": num_open_issues,
                "days_since_last_commit": days_since_last_commit,
                "inverse_simpson_index": inverse_simpson_index,
            },
        )

    def calculate_security(
        self,
        default_branch_protected: bool,
        has_security_policy: bool | None = None,
        has_security_scanning: bool | None = None,
    ) -> DimensionScore:
        """
        Calculate Security dimension.

        Parameters
        ----------
        default_branch_protected : bool
            Whether the default branch is protected
        has_security_policy : bool | None
            Whether the repository publishes a security policy
        has_security_scanning : bool | None
            Whether the repository has automated security scanning configured
        """
        w = self._weights["security"]
        score = _weighted_average(
            {
                "default_branch_protected": (
                    float(default_branch_protected),
                    w["default_branch_protected"],
                ),
                "has_security_policy": (
                    (
                        float(has_security_policy)
                        if has_security_policy is not None
                        else None
                    ),
                    w["has_security_policy"],
                ),
                "has_security_scanning": (
                    (
                        float(has_security_scanning)
                        if has_security_scanning is not None
                        else None
                    ),
                    w["has_security_scanning"],
                ),
            }
        )
        return DimensionScore(
            name="Security",
            score=_clamp(score),
            details={
                "default_branch_protected": default_branch_protected,
                "has_security_policy": has_security_policy,
                "has_security_scanning": has_security_scanning,
            },
        )

    def calculate_scientific_impact(
        self,
        citation_count: int,
        influential_citation_count: int | None,
        max_citations_in_corpus: int,
    ) -> DimensionScore:
        """
        Calculate Scientific Impact dimension.

        Citation counts are normalised logarithmically against the corpus maximum
        to account for scale differences across research areas.

        Parameters
        ----------
        citation_count : int
            Number of citations to the publication
        influential_citation_count : int | None
            Influential citations reported by Semantic Scholar
        max_citations_in_corpus : int
            Maximum citations in the reference corpus (default 1000)
        """
        w = self._weights["scientific_impact"]

        if max_citations_in_corpus <= 0:
            max_citations_in_corpus = 1000

        denominator = math.log(max_citations_in_corpus + 0.5)
        citation_component = (
            math.log(max(citation_count, 0) + 0.5) / denominator
            if denominator > 0
            else 0.0
        )

        influential_component = (
            math.log(max(influential_citation_count, 0) + 0.5) / denominator
            if influential_citation_count is not None and denominator > 0
            else None
        )

        score = _weighted_average(
            {
                "citation_count": (citation_component, w["citation_count"]),
                "influential_citation_count": (
                    influential_component,
                    w["influential_citation_count"],
                ),
            }
        )
        return DimensionScore(
            name="Scientific Impact",
            score=_clamp(score),
            details={
                "citation_count": citation_count,
                "influential_citation_count": influential_citation_count,
                "max_citations_in_corpus": max_citations_in_corpus,
            },
        )

    def calculate_overall_score(
        self, dimensions: list[DimensionScore]
    ) -> DimensionScore:
        """
        Calculate overall maturity score as a weighted average of all dimensions.

        Parameters
        ----------
        dimensions : list[DimensionScore]
            List of dimension scores (must match _DIMENSION_NAMES order).
        """
        if not dimensions or all(dim.score is None for dim in dimensions):
            return DimensionScore(
                name="Overall",
                score=None,
                details={"note": "No dimension scores available."},
            )

        w = self._weights["overall"]

        available_pairs = [
            (dim, name)
            for dim, name in zip(dimensions, _DIMENSION_NAMES)
            if dim.score is not None
        ]

        available_weights = {name: w.get(name, 0.0) for _, name in available_pairs}
        total_weight = sum(available_weights.values())

        if total_weight == 0:
            return DimensionScore(
                name="Overall",
                score=None,
                details={"note": "All dimension weights are zero."},
            )

        normalized_weights = {k: v / total_weight for k, v in available_weights.items()}
        overall_score = sum(
            dim.score * normalized_weights[name] for dim, name in available_pairs
        )

        return DimensionScore(
            name="Overall",
            score=overall_score,
            details={"weights_used": normalized_weights},
        )


# Module-level helpers


def _clamp(value: float) -> float:
    """Clamp a score to [0.0, 1.0]."""
    return min(1.0, max(0.0, value))


def _weighted_average(metrics: dict[str, tuple[float | None, float]]) -> float:
    """Return a weighted average, skipping entries whose value is None.

    Parameters
    ----------
    metrics :
        Mapping of name → (value, weight). Entries with value=None are excluded
        and the remaining weights are renormalised automatically.
    """
    total_weight = sum(w for v, w in metrics.values() if v is not None)
    if total_weight == 0:
        return 0.0
    return sum(v * w for v, w in metrics.values() if v is not None) / total_weight
