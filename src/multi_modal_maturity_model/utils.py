from typing import Any


def get_nested(obj: Any, path: str) -> Any:
    """
    Traverse a nested dict/list using dot-notation path.

    Examples:
        get_nested(data, "open_access.is_oa")
        get_nested(data, "cited_by_count")
    """
    for key in path.split("."):
        if obj is None:
            return None
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list):
            # If we hit a list mid-path, map over it and collect non-None results
            results = [get_nested(item, key) for item in obj]
            obj = [r for r in results if r is not None] or None
        else:
            return None
    return obj
