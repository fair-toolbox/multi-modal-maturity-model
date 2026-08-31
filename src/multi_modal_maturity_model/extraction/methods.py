import logging
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from .calculators import CALCULATORS

logger = logging.getLogger(__name__)


def _get_nested(obj: Any, path: str) -> Any:
    """
    Traverse a nested dict/list using dot-notation path.
    """
    for key in path.split("."):
        if obj is None:
            logger.debug(f"Path '{path}' not found in object; returning None.")
            return None
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list):
            # If we hit a list mid-path, map over it and collect non-None results
            results = [_get_nested(item, key) for item in obj]
            obj = [r for r in results if r is not None] or None
        else:
            logger.debug(
                f"Unexpected type {type(obj)} encountered while traversing path '{path}'"
            )
            return None
    return obj


def extract_direct(source_data: dict[str, Any], path: str) -> Any:
    return _get_nested(source_data, path)


def extract_existence_check(source_data: dict[str, Any], path: str) -> bool:
    value = _get_nested(source_data, path)
    return value is not None and value != "" and value != []


def extract_pattern_match(
    source_data: dict[str, Any],
    path: str,
    patterns_cfg: dict[str, list[str]],
    pattern_group: str,
) -> bool:
    file_list = _get_nested(source_data, path)

    if not file_list:
        logger.debug(
            f"No files found at path '{path}' for pattern matching. Returning False."
        )
        return False

    patterns = patterns_cfg[pattern_group]

    # Extract filenames/paths from file list
    files = []
    for item in file_list:
        if isinstance(item, dict):
            filepath = item.get("path") or item.get("name")
            if filepath:
                files.append(filepath)
        elif isinstance(item, str):
            files.append(item)

    # Check for pattern matches
    for f in files:
        name = Path(f).name.lower()
        for p in patterns:
            pattern = p.lower()
            if fnmatch(name, pattern):
                return True
    return False


def extract_calculated(
    source_data: dict[str, Any], path: str, fn_name: str, params: dict | None
) -> Any:
    fn = CALCULATORS.get(fn_name)
    if fn is None:
        logger.warning(f"Unknown calculator '{fn_name}'. Returning None.")
        return None

    value = _get_nested(source_data, path)
    if value is None:
        logger.debug(
            f"Path '{path}' not found in source data for calculator '{fn_name}'; returning None."
        )
        return None

    return fn(value, **(params or {}))


def extract_publication(papers: dict[str, Any], path: str, aggregation: str) -> Any:
    values = [_get_nested(papers[doi], path) for doi in papers]
    values = [v for v in values if v is not None]

    if not values:
        logger.debug(
            f"No valid values found for publication aggregation '{aggregation}'. Returning None."
        )
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
            return values[0]


EXTRACTION_METHODS = {
    "direct": extract_direct,
    "existence_check": extract_existence_check,
    "pattern_match": extract_pattern_match,
    "calculated": extract_calculated,
    "publication": extract_publication,
}
