"""Async client for OpenAlex API."""

import asyncio
import httpx
import logging
from typing import Any

from .base import BaseClient

logger = logging.getLogger(__name__)


class OpenAlexClient(BaseClient):
    """
    Fetch publication metadata from OpenAlex API.

    Parameters
    ----------
    dois : list[str]
        List of DOIs to fetch data for.
    """

    BASE_URL = "https://api.openalex.org/works/doi:"

    def __init__(self, dois: list[str]):
        self.dois = dois

    async def _fetch_doi(
        self, session: httpx.AsyncClient, doi: str
    ) -> tuple[str, dict | None]:
        """Fetch data for a single DOI."""
        url = f"{self.BASE_URL}{doi}"

        try:
            response = await session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return doi, data

        except httpx.RequestError:
            logger.error(f"Request error fetching data for DOI {doi}")
            return doi, None

        except httpx.HTTPStatusError:
            logger.error(f"HTTP error fetching data for DOI {doi}")
            return doi, None

        except Exception as e:
            logger.error(f"Unexpected error fetching data for DOI {doi}: {e}")
            return doi, None

    async def fetch(self) -> dict[str, Any]:
        """
        Collect publication data from OpenAlex.

        Returns:
        -------
        dict
            Dictionary with raw OpenAlex API responses for each DOI
        """
        results = {}

        async with httpx.AsyncClient(timeout=30) as session:
            tasks = [self._fetch_doi(session, doi) for doi in self.dois]
            results = await asyncio.gather(*tasks, return_exceptions=False)

        return dict(results)
