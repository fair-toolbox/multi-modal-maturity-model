import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from multi_modal_maturity_model.adapters.gitlab_adapter import (
    GitLabAdapter,
    transform_contributors,
    extract_languages,
    detect_license,
)
from multi_modal_maturity_model.adapters.adapters_utils import (
    calculate_avg_time_to_close,
)
from multi_modal_maturity_model.core.models import Contributor, RepositoryMetrics


# ----------------------------
# Helper function tests
# ----------------------------


def test_transform_contributors():
    raw = [
        {"name": "alice", "commits": 5},
        {"name": "bob", "commits": 0},
        {},  # should default to "unknown" and 0
    ]
    result = transform_contributors(raw)
    assert len(result) == 3
    assert result[0] == Contributor(login="alice", total_commits=5)
    assert result[1] == Contributor(login="bob", total_commits=0)
    assert result[2] == Contributor(login="unknown", total_commits=0)


def test_extract_languages():
    langs = {"Python": 1000, "JS": 500}
    result = extract_languages(langs)
    assert set(result) == {"Python", "JS"}

    result_empty = extract_languages(None)
    assert result_empty == []


def test_calculate_avg_time_to_close():
    now = datetime.now(timezone.utc)

    issue1 = SimpleNamespace(
        created_at=(now - timedelta(days=2)).isoformat().replace("+00:00", "Z"),
        closed_at=now.isoformat().replace("+00:00", "Z"),
    )
    issue2 = SimpleNamespace(
        created_at=(now - timedelta(days=4)).isoformat().replace("+00:00", "Z"),
        closed_at=(now - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
    )

    closed_issues = [issue1, issue2]

    avg_days = calculate_avg_time_to_close(closed_issues)
    assert avg_days == pytest.approx(2.5, 0.01)


def test_detect_license():
    tree = [
        {"type": "blob", "name": "README.md"},
        {"type": "blob", "name": "LICENSE"},
    ]
    assert detect_license(tree) is True

    tree_no_license = [{"type": "blob", "name": "README.md"}]
    assert detect_license(tree_no_license) is False

    tree_empty = []
    assert detect_license(tree_empty) is False


# ----------------------------
# GitLabAdapter tests
# ----------------------------


def test_to_repository_metrics_basic():
    raw_data = {
        "repo": {
            "web_url": "https://gitlab.com/example/repo",
            "path_with_namespace": "example/repo",
            "default_branch": "main",
            "star_count": 10,
            "forks_count": 2,
        },
        "open_issues_count": 3,
        "default_branch_protected": True,
        "contributors": [{"name": "alice", "commits": 5}],
        "languages": {"Python": 1234, "JS": 567},
        "closed_issues": [],
        "repository_tree": [{"type": "blob", "name": "LICENSE"}],
    }

    metrics = GitLabAdapter.to_repository_metrics(raw_data)

    assert isinstance(metrics, RepositoryMetrics)
    assert metrics.platform == "gitlab"
    assert metrics.url == "https://gitlab.com/example/repo"
    assert metrics.repo == "example/repo"
    assert metrics.default_branch == "main"
    assert metrics.stars == 10
    assert metrics.forks == 2
    assert metrics.open_issues == 3
    assert metrics.avg_time_to_close_days is None
    assert metrics.default_branch_is_protected is True
    assert set(metrics.languages) == {"Python", "JS"}
    assert metrics.has_license is True
    assert len(metrics.contributors) == 1
    assert metrics.contributors[0] == Contributor(login="alice", total_commits=5)
