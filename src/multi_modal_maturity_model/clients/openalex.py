"""
Client for OpenAlex API.
"""

import logging
import requests

from typing import Any

logger = logging.getLogger(__name__)


class OpenAlexClient:
    """
    Fetch publication metadata from OpenAlex API.
    """

    def __init__(self, base_url: str = "https://api.openalex.org/works"):
        self.base_url = base_url

    def _build_query(
        self, pmid: str | None = None, doi: str | None = None
    ) -> str | None:
        if doi:
            return f"doi:{doi}"
        if pmid:
            return f"pmid:{pmid}"
        return None

    def fetch(
        self, pmid: str | None = None, doi: str | None = None
    ) -> dict[str, Any] | None:
        """
        Get work (paper) by identifier.

        Parameters
        ----------
        pmid : str | None
            PubMed ID of the paper
        doi : str | None
            DOI of the paper

        Returns
        -------
        dict | None
            Work data with citations and more
        """
        query = self._build_query(pmid=pmid, doi=doi)
        if not query:
            logger.error("Cannot fetch work without a valid identifier")
            raise ValueError("Must provide either PMID or DOI to fetch work")

        url = f"{self.base_url}/{query}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.RequestException as e:
            if e.response.status_code == 404:
                logger.info(f"Work not found for query: {query}")
                return None
            logger.error(f"Request error fetching data from OpenAlex: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching work for query {query}: {e}")
            raise
