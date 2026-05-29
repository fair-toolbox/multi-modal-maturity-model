"""altmetric asynchronous API client."""

import asyncio

import httpx
import logging

from typing import Any

from .base import BaseClient

logger = logging.getLogger(__name__)


class AltmetricClient(BaseClient):
    """
    Collect raw altmetric data.

    Parameters
    ----------
    doi : str
        The DOI of the publication for which to fetch altmetric data.
    """

    BASE_URL = "https://api.altmetric.com/v1/doi/"

    def __init__(self, dois: list[str], api_key: str):
        self.dois = dois
        self.api_key = api_key
        self.params = {"key": self.api_key}

    async def _fetch_doi(
        self, session: httpx.AsyncClient, doi: str
    ) -> tuple[str, dict | None]:
        """Fetch data for a single DOI."""
        url = f"{self.BASE_URL}{doi}"

        try:
            response = await session.get(url)
            response.raise_for_status()
            data = response.json()
            return doi, data

        except httpx.RequestError:
            logger.error(f"Request error while fetching data for DOI {doi}")
            return doi, None

        except httpx.HTTPStatusError:
            logger.error(f"HTTP error while fetching data for DOI {doi}")
            return doi, None

        except Exception as e:
            logger.error(f"Unexpected error while fetching data for DOI {doi}: {e}")
            return doi, None

    async def fetch(self) -> dict[str, Any]:
        """
        Collect altmetric data for a given DOI.

        Returns
        -------
        dict
            Dictionary with raw altmetric API response
        """
        async with httpx.AsyncClient(timeout=30, params=self.params) as client:
            tasks = [self._fetch_doi(client, doi) for doi in self.dois]
            results = await asyncio.gather(*tasks, return_exceptions=False)

        return dict(results)
