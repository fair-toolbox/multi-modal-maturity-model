"""Metric extraction from raw data sources."""

import fnmatch
import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from .utils import get_nested

logger = logging.getLogger(__name__)

_EDAM_DATA = None


def _load_edam_data() -> dict[str, Any]:
    """Load EDAM format ontology data from bundled JSON file."""
    global _EDAM_DATA
    if _EDAM_DATA is None:
        edam_path = Path(__file__).parent / "data" / "edam_format.json"
        with open(edam_path) as f:
            _EDAM_DATA = json.load(f)
    return _EDAM_DATA


# Calculated functions


def calculate_days_since_last_commit(source_cfg: dict, raw_data: dict) -> int | None:
    """
    Calculate days since the last commit.

    Parameters
    ----------
    source_cfg : dict
        Source configuration containing 'path' to timestamp field
    raw_data : dict
        Raw data from the source (GitHub or GitLab)

    Returns
    -------
    int | None
        Number of days since last commit, or None if timestamp not found
    """
    timestamp_str = get_nested(raw_data, source_cfg["path"])
    if not timestamp_str:
        return None

    try:
        # Parse ISO 8601 timestamp
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(timestamp.tzinfo)
        delta = now - timestamp
        return int(delta.total_seconds() / 86400)  # Convert to days
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
        return None


def calculate_avg_time_to_close(source_cfg: dict, raw_data: dict) -> float | None:
    """
    Calculate average time to close issues in days.

    Parameters
    ----------
    source_cfg : dict
        Source configuration containing 'path' to closed issues list
    raw_data : dict
        Raw data from the source (GitHub or GitLab)

    Returns
    -------
    float | None
        Average days to close issues, or None if no issues found
    """
    issues = get_nested(raw_data, source_cfg["path"])
    if not issues:
        return None

    close_times = []
    for issue in issues:
        created_at_str = issue.get("created_at")
        closed_at_str = issue.get("closed_at")

        if not created_at_str or not closed_at_str:
            continue

        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            closed_at = datetime.fromisoformat(closed_at_str.replace("Z", "+00:00"))
            delta = closed_at - created_at
            close_times.append(delta.total_seconds() / 86400)  # Convert to days
        except (ValueError, AttributeError) as e:
            logger.debug(f"Failed to parse issue timestamps: {e}")
            continue

    if not close_times:
        return None

    return sum(close_times) / len(close_times)


def calculate_inverse_simpson_index(source_cfg: dict, raw_data: dict) -> float | None:
    """
    Calculate contributor diversity using inverse Simpson index.

    The inverse Simpson index is 1 / Σ(p_i²) where p_i is the proportion
    of contributions by contributor i. Higher values indicate more diverse
    contribution patterns.

    Parameters
    ----------
    source_cfg : dict
        Source configuration containing:
        - 'path': path to contributors list
        - 'params': dict with 'login_key' and 'commits_key'
    raw_data : dict
        Raw data from the source (GitHub or GitLab)

    Returns
    -------
    float | None
        Inverse Simpson diversity index, or None if insufficient data
    """
    contributors = get_nested(raw_data, source_cfg["path"])
    if not contributors:
        return None

    params = source_cfg.get("params", {})
    commits_key = params.get("commits_key", "contributions")

    # Extract commit counts
    commit_counts = []
    for contributor in contributors:
        count = contributor.get(commits_key)
        if count is not None and count > 0:
            commit_counts.append(count)

    if not commit_counts:
        return None

    # Calculate Simpson index
    total_commits = sum(commit_counts)
    if total_commits == 0:
        return None

    simpson_index = sum((count / total_commits) ** 2 for count in commit_counts)

    # Return inverse (avoid division by zero)
    if simpson_index > 0:
        return 1.0 / simpson_index
    return None


def calculate_edam_leaf_fraction(source_cfg: dict, raw_data: dict) -> float | None:
    """
    Calculate fraction of EDAM terms that are leaf nodes.

    Leaf nodes are terms with no children (num_children == 0) in the
    EDAM ontology, indicating the most specific data format classifications.

    Parameters
    ----------
    source_cfg : dict
        Source configuration containing:
        - 'path': path to function list
        - 'data_type': 'input' or 'output'
    raw_data : dict
        Raw data from bio.tools

    Returns
    -------
    float | None
        Fraction of EDAM terms that are leaf nodes (0.0 to 1.0),
        or None if no EDAM terms found
    """
    functions = get_nested(raw_data, source_cfg["path"])
    if not functions:
        return None

    data_type = source_cfg.get("data_type", "input")
    edam_data = _load_edam_data()
    all_terms = edam_data.get("all_terms", {})

    # Collect EDAM term URIs from function descriptors
    edam_uris = set()
    for func in functions:
        if not isinstance(func, dict):
            continue

        # Look for input or output data formats
        data_list = func.get(data_type, [])
        for data_item in data_list:
            if not isinstance(data_item, dict):
                continue

            # Extract EDAM format URI
            format_info = data_item.get("format", [])
            for fmt in format_info:
                if isinstance(fmt, dict):
                    uri = fmt.get("uri")
                    if uri:
                        edam_uris.add(uri)

    if not edam_uris:
        return None

    # Count leaf nodes
    leaf_count = 0
    for uri in edam_uris:
        term_info = all_terms.get(uri, {})
        if term_info.get("num_children", 0) == 0:
            leaf_count += 1

    return leaf_count / len(edam_uris)


# Registry of calculated functions
CALCULATED_FUNCTIONS = {
    "calculate_days_since_last_commit": calculate_days_since_last_commit,
    "calculate_avg_time_to_close": calculate_avg_time_to_close,
    "calculate_inverse_simpson_index": calculate_inverse_simpson_index,
    "calculate_edam_leaf_fraction": calculate_edam_leaf_fraction,
}


# Per-method extractors


def _extract_direct(source_cfg: dict, raw_data: dict) -> Any:
    """
    Extract value directly from a nested path.

    Parameters
    ----------
    source_cfg : dict
        Configuration with 'path' key
    raw_data : dict
        Raw data to extract from

    Returns
    -------
    Any
        Extracted value or None if not found
    """
    return get_nested(raw_data, source_cfg["path"])


def _extract_existence_check(source_cfg: dict, raw_data: dict) -> bool:
    """
    Check if a value exists at the given path.

    Parameters
    ----------
    source_cfg : dict
        Configuration with 'path' key
    raw_data : dict
        Raw data to check

    Returns
    -------
    bool
        True if value exists and is non-empty, False otherwise
    """
    value = get_nested(raw_data, source_cfg["path"])
    return value is not None and value != "" and value != []


def _extract_pattern_match(source_cfg: dict, raw_data: dict, patterns: dict) -> bool:
    """
    Check whether any file in the repository tree matches a pattern group.

    Parameters
    ----------
    source_cfg : dict
        Configuration with 'pattern_group' and 'path' keys
    raw_data : dict
        Raw data containing file list
    patterns : dict
        Loaded patterns.yaml dict, keyed by pattern_group name

    Returns
    -------
    bool
        True if any file matches any pattern in the group, False otherwise
    """
    group_name = source_cfg.get("pattern_group")
    file_list = get_nested(raw_data, source_cfg["path"])

    if not file_list or not group_name or group_name not in patterns:
        return False

    group_patterns = patterns[group_name]

    # Flatten nested pattern structure if needed
    all_patterns = []
    if isinstance(group_patterns, dict):
        # Pattern group has subcategories (e.g., workflow_files.cwl)
        for subpatterns in group_patterns.values():
            if isinstance(subpatterns, list):
                all_patterns.extend(subpatterns)
            else:
                all_patterns.append(subpatterns)
    elif isinstance(group_patterns, list):
        all_patterns = group_patterns
    else:
        return False

    # Extract filenames/paths from file list
    filenames = []
    for item in file_list:
        if isinstance(item, dict):
            filename = item.get("path") or item.get("name")
            if filename:
                filenames.append(filename)
        elif isinstance(item, str):
            filenames.append(item)

    # Check for pattern matches (case-insensitive)
    for filename in filenames:
        filename_lower = filename.lower()
        for pattern in all_patterns:
            pattern_lower = pattern.lower()
            # Use fnmatch for glob patterns
            if fnmatch.fnmatch(filename_lower, pattern_lower):
                return True

    return False


def _extract_calculated(
    metric_name: str, source_name: str, source_cfg: dict, raw_data: dict
) -> Any:
    """
    Apply a calculated function to extract a metric.

    Parameters
    ----------
    metric_name : str
        Name of the metric (for logging)
    source_name : str
        Name of the source (for logging)
    source_cfg : dict
        Configuration with 'function' key
    raw_data : dict
        Raw data to process

    Returns
    -------
    Any
        Calculated value or None on error
    """
    fn_name = source_cfg.get("function")
    fn = CALCULATED_FUNCTIONS.get(fn_name)
    if fn is None:
        logger.warning(
            f"[{metric_name}] Unknown calculated function '{fn_name}' "
            f"for source '{source_name}'"
        )
        return None

    try:
        return fn(source_cfg, raw_data)
    except Exception as e:
        logger.error(
            f"[{metric_name}] Error in calculated function '{fn_name}' "
            f"for source '{source_name}': {e}"
        )
        return None


def _extract_publication(source_cfg: dict, papers: list[dict], aggregation: str) -> Any:
    """
    Merge values from multiple papers into a single value for one source.

    Parameters
    ----------
    source_cfg : dict
        Configuration with 'path' key
    papers : list[dict]
        List of paper dictionaries
    aggregation : str
        Aggregation method: 'sum', 'any', 'max', or 'mean'

    Returns
    -------
    Any
        Aggregated value or None if no values found
    """
    path = source_cfg["path"]
    values = [get_nested(p, path) for p in papers]
    values = [v for v in values if v is not None]

    if not values:
        return None

    match aggregation:
        case "sum":
            return sum(values)
        case "any":
            return any(values)
        case "max":
            return max(values)
        case "mean":
            return sum(values) / len(values)
        case _:
            logger.warning(
                f"Unknown aggregation '{aggregation}', falling back to first value"
            )
            return values[0]


# Main extractors


def extract_metric(
    metric_name: str,
    metric_cfg: dict,
    results: dict[str, Any],
    patterns: dict | None = None,
    publication_results: dict[str, list[dict]] | None = None,
) -> dict[str, Any]:
    """
    Extract a single metric value from collected source data.

    Parameters
    ----------
    metric_name : str
        The metric key (used for logging)
    metric_cfg : dict
        The metric's config dict from metrics.yaml
    results : dict[str, Any]
        Collected raw data keyed by source name,
        e.g. results["github"], results["biotools"], ...
    patterns : dict | None, optional
        Loaded patterns.yaml dict (required for pattern_match metrics)
    publication_results : dict[str, list[dict]] | None, optional
        Papers per source, e.g. {"openalex": [...], "europepmc": [...]}.
        Required for publication-method metrics.

    Returns
    -------
    dict[str, Any]
        Dictionary of {source_name: extracted_value} for all sources
        that provided data for this metric
    """
    extraction = metric_cfg.get("extraction", {})
    method = extraction.get("method")
    sources_cfg = extraction.get("sources", {})

    candidate_values: dict[str, Any] = {}

    # --- publication (two-phase) ---
    if method == "publication":
        aggregation = extraction.get("aggregation", "sum")
        for source_name, source_cfg in sources_cfg.items():
            papers = (publication_results or {}).get(source_name, [])
            if not papers:
                continue
            value = _extract_publication(source_cfg, papers, aggregation)
            if value is not None:
                candidate_values[source_name] = value
        return candidate_values

    # --- other methods ---
    for source_name, source_cfg in sources_cfg.items():
        raw_data = results.get(source_name)
        if raw_data is None:
            continue

        try:
            if method == "direct":
                value = _extract_direct(source_cfg, raw_data)

            elif method == "existence_check":
                value = _extract_existence_check(source_cfg, raw_data)

            elif method == "pattern_match":
                if patterns is None:
                    logger.warning(
                        f"[{metric_name}] pattern_match requires patterns dict"
                    )
                    value = None
                else:
                    value = _extract_pattern_match(source_cfg, raw_data, patterns)

            elif method == "calculated":
                # Merge top-level function name from extraction with source_cfg
                merged_cfg = {"function": extraction.get("function"), **source_cfg}
                value = _extract_calculated(
                    metric_name, source_name, merged_cfg, raw_data
                )

            else:
                logger.warning(f"[{metric_name}] Unknown extraction method '{method}'")
                value = None

        except Exception as e:
            logger.error(f"[{metric_name}] Error extracting from '{source_name}': {e}")
            value = None

        if value is not None:
            candidate_values[source_name] = value

    return candidate_values


def extract_all_metrics(
    metrics_cfg: dict,
    results: dict[str, Any],
    patterns: dict | None = None,
    publication_results: dict[str, list[dict]] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Extract all metrics defined in metrics.yaml.

    Parameters
    ----------
    metrics_cfg : dict
        The top-level 'metrics' dict from metrics.yaml
    results : dict[str, Any]
        Raw collected data keyed by source name
    patterns : dict | None, optional
        Loaded patterns.yaml (for pattern_match metrics)
    publication_results : dict[str, list[dict]] | None, optional
        Papers per publication source

    Returns
    -------
    dict[str, dict[str, Any]]
        Dictionary of {metric_name: {source_name: value}}.
        Preserves all source values for each metric.
    """
    extracted = {}
    for metric_name, metric_cfg in metrics_cfg.items():
        extracted[metric_name] = extract_metric(
            metric_name,
            metric_cfg,
            results,
            patterns=patterns,
            publication_results=publication_results,
        )
    return extracted
