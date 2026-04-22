from dataclasses import dataclass
from typing import Any


@dataclass
class ToolModel:
    biotools_id: str
    function: list[Function] | None


@dataclass
class Function:
    operation: list[EDAMItem]
    input: list[DataItem] | None
    output: list[DataItem] | None


@dataclass
class DataItem:
    data: EDAMItem
    format: list[EDAMItem] | None


@dataclass
class EDAMItem:
    uri: str
    term: str


#####################


@dataclass
class Contributor:
    login: str
    total_commits: int


@dataclass
class RepositoryMetrics:
    platform: str
    url: str
    repo: str
    default_branch: str
    stars: int
    forks: int
    open_issues: int
    avg_time_to_close_days: float | None
    default_branch_is_protected: bool | None
    languages: list[str]
    last_commit_date: str | None
    contributors: list[Contributor]
    has_license: bool
    has_workflow_integration: bool | None
    has_distribution_support: bool | None
    has_security_policy: bool | None
    has_security_scanning: bool | None
    inverse_simpson_index: float | None


@dataclass
class CodeQualityMetrics:
    total_nloc: int | None
    total_ccn: int | None
    avg_ccn: float | None
    duplicate_rate: float | None


@dataclass
class HowfairisMetrics:
    license: bool
    repository: bool
    registry: bool
    citation: bool
    checklist: bool


@dataclass
class PublicationMetrics:
    doi: str | None
    pmid: str | None
    citation_count: int | None
    fwci: float | None
    influential_citation_count: int | None
    altmetric_score: float | None
    is_open_access: bool | None


@dataclass
class DimensionScore:
    """Score for a single maturity dimension."""

    name: str
    score: float | None
    details: dict[str, Any] | None = None


@dataclass
class MaturityProfile:
    """Maturity profile for a project/research software."""

    compatibility: DimensionScore
    fairness: DimensionScore
    maintainability: DimensionScore
    sustainability: DimensionScore
    security: DimensionScore
    scientific_impact: DimensionScore
    overall_score: DimensionScore
