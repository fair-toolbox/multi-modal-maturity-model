"""
EuropePMC API client for citation metrics and open access status.
"""

import logging
import re
from typing import Any

import requests

logger = logging.getLogger(__name__)


class EuropePMCError(Exception):
    """Base exception for EuropePMC client errors."""

    pass


class EuropePMCClient:
    """
    Collect citation counts and open access status from EuropePMC API.

    Uses connection pooling for multiple requests.
    """

    def __init__(
        self,
        base_url: str = "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        timeout: int = 30,
    ):
        """
        Initialize the EuropePMC client.

        Parameters
        ----------
        base_url : str
            Base URL for EuropePMC API
        timeout : int
            Request timeout in seconds (default: 30)
        """
        self.base_url = base_url
        self.timeout = timeout

    def fetch(self, pmid: str) -> dict[str, Any]:
        """
        Collect citation metrics for a single PMID.

        Parameters
        ----------
        pmid : str
            PubMed ID (e.g., "12345678")

        Returns
        -------
        dict
            Dictionary with citation count and open access status
            Keys: pmid, citation_count, is_open_access

        Raises
        ------
        InvalidPMIDError
            If PMID format is invalid
        requests.RequestException
            If API call fails
        EuropePMCError
            If data extraction fails
        """
        logger.debug(f"Fetching citation data for PMID: {pmid}")

        try:
            data = self._fetch_publication_data(pmid)
            result_item = self._get_first_result(data)

            if result_item is None:
                logger.warning(f"No results found for PMID {pmid}")
                return {
                    "pmid": pmid,
                    "citation_count": None,
                    "is_open_access": None,
                }

            result = {
                "pmid": pmid,
                "citation_count": self._extract_citation_count(result_item),
                "is_open_access": self._extract_open_access_status(result_item),
            }

            logger.info(f"Successfully collected data for PMID {pmid}")
            return result

        except requests.RequestException as e:
            logger.error(f"API request failed for PMID {pmid}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for PMID {pmid}: {e}")
            raise EuropePMCError(f"Failed to fetch data for PMID {pmid}") from e

    def _fetch_publication_data(self, pmid: str) -> dict[str, Any]:
        """
        Fetch raw publication data from EuropePMC API.

        Parameters
        ----------
        pmid : str
            PubMed ID

        Returns
        -------
        dict
            Raw JSON response from API

        Raises
        ------
        requests.RequestException
            If request fails
        """
        query = f"EXT_ID:{pmid} AND SRC:MED"
        params = {
            "query": query,
            "format": "json",
        }

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

    def _extract_citation_count(self, result_item: dict[str, Any]) -> int | None:
        """
        Extract citation count from a publication result.
        """
        cited_by = result_item.get("citedByCount")
        if cited_by is None:
            return None

        try:
            return int(cited_by)
        except (ValueError, TypeError):
            logger.warning(f"Invalid citation count value: {cited_by}")
            return None

    def _extract_open_access_status(self, result_item: dict[str, Any]) -> bool | None:
        """
        Extract open access status from a publication result.

        """
        is_oa = result_item.get("isOpenAccess")
        if is_oa is None:
            return None

        # API returns "Y" or "N"
        if isinstance(is_oa, str):
            return is_oa.upper() == "Y"

        logger.warning(f"Unexpected open access value type: {type(is_oa)}")
        return None
