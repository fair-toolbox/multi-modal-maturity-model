from dataclasses import dataclass


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
    has_license: bool
    contributors: list[Contributor]


@dataclass
class CodeQualityMetrics:
    total_nloc: int | None
    total_ccn: int | None
    avg_ccn: float | None
    duplicate_rate: float | None


@dataclass
class Contributor:
    login: str
    total_commits: int


@dataclass
class DimensionScore:
    """Score for a single maturity dimension."""

    name: str
    score: float


@dataclass
class MaturityProfile:
    """Maturity profile for a project/research software."""

    url: str
    compatibility: DimensionScore
    fairness: DimensionScore
    maintainability: DimensionScore
    sustainability: DimensionScore
    security: DimensionScore
    scientific_impact: DimensionScore
    overall_score: float
