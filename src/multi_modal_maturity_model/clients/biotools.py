"""bio.tools asynchronous API client."""

import httpx
import logging

from typing import Any

from .base import BaseClient

logger = logging.getLogger(__name__)


class BioToolsClient(BaseClient):
    """
    Collect raw tool metadata from bio.tools registry.

    Parameters
    ----------
    biotools_id : str
        The identifier of the tool in bio.tools.
    """

    BASE_URL = "https://bio.tools/api/tool/"

    def __init__(self, biotools_id: str):
        self.biotools_id = biotools_id

    async def fetch(self) -> dict[str, Any] | None:
        """
        Collect tool metadata from bio.tools.

        Returns
        -------
        dict | None
            Dictionary with raw bio.tools API response or None if fetch fails
        """
        url = f"{self.BASE_URL}{self.biotools_id}?format=json"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                tool = response.json()
                return tool

        except httpx.RequestError as e:
            logger.error(f"Error while fetching {url}: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error code {e.response.status_code} for {url}")
            return None
