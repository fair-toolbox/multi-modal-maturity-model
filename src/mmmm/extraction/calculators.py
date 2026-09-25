import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


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


def calculate_days_since_last_commit(timestamp_str: str) -> int | None:
    """
    Calculate days since the last commit.
    """
    # Parse ISO 8601 timestamp
    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    now = datetime.now(timestamp.tzinfo)
    delta = now - timestamp
    return int(delta.total_seconds() / 86400)  # Convert to days


def calculate_avg_time_to_close(issues: dict) -> float | None:
    """
    Calculate average time to close issues in days.
    """
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
        logger.debug("No valid issue close times found for average calculation.")
        return None

    return sum(close_times) / len(close_times)


def calculate_inverse_simpson_index(
    contributors: dict, commits_key: str = "contributions"
) -> float | None:
    """
    Calculate contributor diversity using inverse Simpson index.
    The inverse Simpson index is calculated as:
        D = 1 / sum(p_i^2)
    where p_i is the proportion of contributions by contributor i.
    """
    commit_counts = []
    for contributor in contributors:
        count = contributor.get(commits_key)
        if count is not None and count > 0:
            commit_counts.append(count)

    if not commit_counts:
        logger.debug(
            "No valid commit counts found for inverse Simpson index calculation."
        )
        return None

    total_commits = sum(commit_counts)
    if total_commits == 0:
        logger.debug("Total commit count is zero.")
        return None

    simpson_index = sum((count / total_commits) ** 2 for count in commit_counts)

    if simpson_index > 0:
        return 1.0 / simpson_index
    return None


def calculate_edam_leaf_fraction(
    functions: dict, data_type: str = "input"
) -> float | None:
    """
    Calculate fraction of EDAM terms that are leaf nodes.

    Leaf nodes are terms with no children (num_children == 0) in the
    EDAM ontology, indicating the most specific data format classifications.
    """
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
        logger.debug("No valid EDAM URIs found for leaf fraction calculation.")
        return None

    # Count leaf nodes
    leaf_count = 0
    for uri in edam_uris:
        term_info = all_terms.get(uri, {})
        if term_info.get("num_children", 0) == 0:
            leaf_count += 1

    return leaf_count / len(edam_uris)


CALCULATORS = {
    "calculate_days_since_last_commit": calculate_days_since_last_commit,
    "calculate_avg_time_to_close": calculate_avg_time_to_close,
    "calculate_inverse_simpson_index": calculate_inverse_simpson_index,
    "calculate_edam_leaf_fraction": calculate_edam_leaf_fraction,
}
