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
    last_commit_date: str | None
    branches_total: int
    branches_protected: int
    default_branch_is_protected: bool | None
    languages: list[str]
    has_license: bool
    contributors: list[Contributor]


@dataclass
class Contributor:
    login: str
    total_commits: int
