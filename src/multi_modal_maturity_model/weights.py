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
    "cnn": 0.2,
    "avg_ccn": 0.25,
    "duplicate_rate": 0.25,
    "lang_penalty": 0,
}

SUSTAINABILITY = {
    "avg_time_to_close": 0.4,
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
    "citation_count": 0.7,
    "influential_citation_count": 0.3,
}

OVERALL = {
    "compatibility": 0.25,
    "fairness": 0.25,
    "maintainability": 0.2,
    "scientific_impact": 0.1,
    "security": 0.1,
    "sustainability": 0.2,
}
