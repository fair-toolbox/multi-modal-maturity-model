COMPATIBILITY = {
    "input_formats": 0.25,
    "output_formats": 0.25,
    "workflow_support": 0.25,
    "distribution_support": 0.25,
}

FAIRNESS = {
    "license": 0.2,
    "repository": 0.3,
    "registry": 0.2,
    "citation": 0.1,
    "checklist": 0.1,
    "publication_oa": 0.1,
}

MAINTAINABILITY = {
    "nloc": 0.3,
    "ccn": 0.2,
    "avg_ccn": 0.25,
    "duplicate_rate": 0.25,
}

SUSTAINABILITY = {
    "avg_issue_close_time_days": 0.4,
    "num_open_issues": 0.3,
    "days_since_last_commit": 0.2,
    "inverse_simpson_index": 0.1,
}

SECURITY = {
    "default_branch_protected": 0.34,
    "has_security_policy": 0.33,
    "has_security_scanning": 0.33,
}

SCIENTIFIC_IMPACT = {
    "fwci": 0.4,
    "citation_count": 0.3,
    "influential_citation_count": 0.2,
    "altmetric_score": 0.1,
}

OVERALL = {
    "compatibility": 0.25,
    "fairness": 0.25,
    "maintainability": 0.2,
    "scientific_impact": 0.1,
    "security": 0.1,
    "sustainability": 0.2,
}

_DEFAULTS: dict[str, dict[str, float]] = {
    "compatibility": COMPATIBILITY,
    "fairness": FAIRNESS,
    "maintainability": MAINTAINABILITY,
    "sustainability": SUSTAINABILITY,
    "security": SECURITY,
    "scientific_impact": SCIENTIFIC_IMPACT,
    "overall": OVERALL,
}

REQUIRED_METRICS = {
    dimension: set(weights.keys()) for dimension, weights in _DEFAULTS.items()
}


def validate_weights(custom_weights: dict[str, dict[str, float]]) -> None:
    """
    Validate that custom weights are complete for each dimension provided.
    """
    for dimension, weights in custom_weights.items():
        if dimension not in REQUIRED_METRICS:
            raise ValueError(
                f"Unknown dimension '{dimension}'. "
                f"Valid dimensions: {', '.join(REQUIRED_METRICS.keys())}"
            )

        required = REQUIRED_METRICS[dimension]
        provided = set(weights.keys())

        if provided != required:
            missing = required - provided
            extra = provided - required
            parts = [f"Incomplete weights for '{dimension}' dimension."]
            if missing:
                parts.append(f"Missing metrics: {', '.join(sorted(missing))}")
            if extra:
                parts.append(f"Unknown metrics: {', '.join(sorted(extra))}")
            parts.append(f"Required metrics: {', '.join(sorted(required))}")
            raise ValueError(" ".join(parts))


def build_weights(
    custom: dict[str, dict[str, float]] | None = None
) -> dict[str, dict[str, float]]:
    """
    Build a complete weights configuration, merging custom overrides with defaults.
    """
    config = {k: v.copy() for k, v in _DEFAULTS.items()}
    if custom:
        validate_weights(custom)
        for dimension, weights in custom.items():
            config[dimension] = weights.copy()
    return config
