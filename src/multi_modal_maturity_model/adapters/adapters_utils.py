"""
Shared utility functions for adapters.
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def get_datetime_field(item: Any, field_name: str) -> str | None:
    """
    Extract a datetime field from either a dict or object.
    """
    if isinstance(item, dict):
        return item.get(field_name)
    else:
        return getattr(item, field_name, None)


def calculate_avg_time_to_close(closed_issues: list[Any] | None) -> float | None:
    """
    Calculate average time to close issues in days.
    Works with both dict-based (GitHub) and object-based (GitLab) issue data.
    """
    if not closed_issues:
        return None

    total_days = 0
    count = 0

    for issue in closed_issues:
        created_at = get_datetime_field(issue, "created_at")
        closed_at = get_datetime_field(issue, "closed_at")

        if created_at and closed_at:
            try:
                created = parse_iso_datetime(created_at)
                closed = parse_iso_datetime(closed_at)
                days = (closed - created).total_seconds() / 86400  # Convert to days
                total_days += days
                count += 1
            except (ValueError, AttributeError) as e:
                logger.debug(f"Could not parse issue dates: {e}")
                continue

    if count == 0:
        return None

    return round(total_days / count, 2)
