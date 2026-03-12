"""
EuropePMC API client for citation metrics and open access status.
"""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class EuropePMCClient:
    """
    Collect citation counts and open access status from EuropePMC API.
    """

    def __init__(
        self, base_url: str = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    ):
        """
        Parameters
        ----------
        base_url : str
            EuropePMC API base URL
        """
        self.base_url = base_url
        logger.info("EuropePMCCollector initialized")

    def collect(self, pmid: str) -> dict[str, Any]:
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
        requests.RequestException
            If API call fails
        """
        logger.debug(f"Fetching citation data for PMID: {pmid}")

        try:
            data = self._fetch_publication_data(pmid)

            result = {
                "pmid": pmid,
                "citation_count": self._extract_citation_count(data),
                "is_open_access": self._extract_open_access_status(data),
            }

            logger.info(f"Successfully collected data for PMID {pmid}")
            return result

        except requests.RequestException as e:
            logger.error(f"Request error for PMID {pmid}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for PMID {pmid}: {e}")
            raise

    def collect_batch(self, pmids: list[str]) -> list[dict[str, Any]]:
        """
        Collect citation metrics for multiple PMIDs.

        Parameters
        ----------
        pmids : list[str]
            List of PubMed IDs

        Returns
        -------
        list[dict]
            List of dictionaries with citation data for each PMID
        """
        results = []

        for pmid in pmids:
            try:
                result = self.collect(pmid)
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to collect data for PMID {pmid}: {e}")
                # Return None values for failed requests
                results.append(
                    {
                        "pmid": pmid,
                        "citation_count": None,
                        "is_open_access": None,
                    }
                )

        return results

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

        response = requests.get(self.base_url, params=params, timeout=30)
        response.raise_for_status()

        return response.json()

    def _extract_citation_count(self, data: dict[str, Any]) -> int | None:
        """
        Extract citation count from API response.

        Parameters
        ----------
        data : dict
            Raw API response

        Returns
        -------
        int | None
            Citation count, or None if not available
        """
        try:
            result = data["resultList"]["result"][0]
            count = int(result.get("citedByCount", 0))
            return count
        except (IndexError, KeyError, ValueError) as e:
            logger.warning(f"Could not extract citation count: {e}")
            return None

    def _extract_open_access_status(self, data: dict[str, Any]) -> bool | None:
        """
        Extract open access status from API response.

        Parameters
        ----------
        data : dict
            Raw API response

        Returns
        -------
        bool | None
            True if open access, False if not, None if unknown
        """
        try:
            result = data["resultList"]["result"][0]
            is_oa = result.get("isOpenAccess", None)

            if is_oa is not None:
                # API returns "Y" or "N"
                return is_oa.lower() == "y"

            return None

        except (IndexError, KeyError) as e:
            logger.warning(f"Could not extract open access status: {e}")
            return None
