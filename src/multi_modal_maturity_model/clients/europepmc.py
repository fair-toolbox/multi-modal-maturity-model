"""Async client for Europe PMC API."""

import asyncio
import httpx
import logging
from typing import Any

from .base import BaseClient

logger = logging.getLogger(__name__)


class EuropePMCClient(BaseClient):
    """
    Fetch publication metadata from Europe PMC API.

    Parameters
    ----------
    dois : list[str]
        List of DOIs to fetch data for.
    """

    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def __init__(self, dois: list[str]):
        self.dois = dois

    async def _fetch_doi(
        self, session: httpx.AsyncClient, doi: str
    ) -> tuple[str, dict | None]:
        """Fetch data for a single DOI."""

        url = f"{self.BASE_URL}?query=doi:{doi}&format=json"

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
        Collect publication data from Europe PMC.

        Returns:
        -------
        dict
            Dictionary with raw Europe PMC API responses for each DOI
        """
        results = {}

        async with httpx.AsyncClient(timeout=30) as session:
            tasks = [self._fetch_doi(session, doi) for doi in self.dois]
            results = await asyncio.gather(*tasks, return_exceptions=False)

        return dict(results)
