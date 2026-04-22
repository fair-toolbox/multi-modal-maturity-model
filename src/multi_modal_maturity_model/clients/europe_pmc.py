"""
Client for Europe PMC API.
"""

import logging
import requests

from typing import Any

logger = logging.getLogger(__name__)


class EuropePMCClient:
    """
    Fetch publication metadata from EuropePMC API.
    """

    def __init__(
        self,
        base_url: str = "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        timeout: int = 30,
    ):
        self.base_url = base_url
        self.timeout = timeout

    def _build_query(self, pmid: str | None = None, doi: str | None = None) -> str:
        if pmid:
            return f"EXT_ID:{pmid} AND SRC:MED"
        if doi:
            return f"DOI:{doi}"
        return None

    def _fetch_publication_data(self, query: str) -> dict[str, Any]:
        """
        Fetch raw publication data from EuropePMC API.
        """
        params = {"query": query, "format": "json"}

        response = requests.get(self.base_url, params=params, timeout=self.timeout)
        response.raise_for_status()

        return response.json()

    def _get_first_result(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        Extract the first result from API response.

        Parameters
        ----------
        payload : dict
            API response payload

        Returns
        -------
        dict | None
            First result or None if no results found
        """
        results = payload.get("resultList", {}).get("result") or []
        return results[0] if results else None

    def fetch(
        self, pmid: str | None = None, doi: str | None = None
    ) -> dict[str, Any] | None:
        """
        Fetch citation metrics for a single DOI or PMID.

        Parameters
        ----------
        pmid : str | None
            PubMed ID (e.g., "12345678")
        doi : str | None
            DOI (e.g., "10.1038/nature12373")

        Returns
        -------
        dict
            Raw EuropePMC data for the requested publication.

        Raises
        ------
        requests.RequestException
            If API call fails
        ValueError
            If neither PMID nor DOI is provided
        """
        identifier = pmid or doi
        identifier_type = "pmid" if pmid else "doi"

        if not identifier:
            raise ValueError("Must provide either PMID or DOI")

        try:
            query = self._build_query(pmid=pmid, doi=doi)
            data = self._fetch_publication_data(query=query)
            result_item = self._get_first_result(data)

            if not result_item:
                logger.info(f"No results found for {identifier_type}:{identifier}")

            return result_item

        except requests.RequestException as e:
            if e.response and e.response.status_code == 404:
                logger.info(f"Publication not found: {identifier_type}:{identifier}")
                return None
            raise
        except Exception:
            raise
