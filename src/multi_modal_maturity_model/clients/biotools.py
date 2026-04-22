"""
Fetches tool metadata from the bio.tools API.
"""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class BioToolsClient:
    """
    Collect bio.tools metadata from the bio.tools API.

    Parameters
    ----------
    base_url : str
        Base URL for the bio.tools API (default: "https://bio.tools/api/tool")
    """

    def __init__(self, base_url: str = "https://bio.tools/api/tool"):
        self.base_url = base_url

    def _get(self, tool_id: str) -> dict[str, Any]:
        url = f"{self.base_url}/{tool_id}?format=json"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            logger.error(f"Error fetching data from bio.tools for ID {tool_id}: {e}")
            raise

    def fetch(self, tool_id: str) -> dict[str, Any]:
        """
        Fetch bio.tools metadata for a given tool ID.

        Parameters
        ----------
        tool_id : str
            The bio.tools ID of the tool to fetch

        Returns
        -------
        dict
            Dictionary containing the tool metadata.
        """
        data = self._get(tool_id)
        logger.info(f"Successfully collected bio.tools entry {tool_id}")
        return data
