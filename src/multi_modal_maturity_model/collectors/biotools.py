"""
Fetches tool metadata from the bio.tools API.
"""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

class BioToolsCollector:
    """Collect bio.tools metadata."""

    def __init__(self, base_url: str = "https://bio.tools/api/tool"):

        self.base_url = base_url
        logger.info("bio.tools collector initialized")

    def collect(self, tool_id: str) -> dict[str, Any]:
        logger.debug(f"Fetching tool data for biotoolsID: {tool_id}")

        try:
            data = self._fetch_tool_data(tool_id)

            return data

        except requests.RequestException as e:
            logger.error(f"Failed to fetch biotoolsID {tool_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching tool {tool_id}: {e}")
            raise

    def _fetch_tool_data(self, tool_id: str) -> dict[str, Any]:
        url = f"{self.base_url}/{tool_id}"
        logger.debug(f"Requesting URL: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
