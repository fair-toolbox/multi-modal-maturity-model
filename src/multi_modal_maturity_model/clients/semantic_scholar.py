import logging
import requests
from typing import Any

logger = logging.getLogger(__name__)


class SemanticScholarClient:
    """
    Free API for collecting citation metrics and scientific impact.
    """

    def __init__(
        self,
        base_url: str = "https://api.semanticscholar.org/graph/v1",
        timeout: int = 30,
    ):
        """
        Initialize the Semantic Scholar client.
        """
        self.base_url = base_url
        self.timeout = timeout

    def fetch(self, doi: str) -> dict[str, Any] | None:
        """
        Get paper metrics by DOI.

        Parameters
        ----------
        doi : str
            DOI of the paper (e.g., "10.1186/s13059-019-1772-6")

        Returns
        -------
        dict | None
            Paper data with citation metrics, or None if not found
        """
        url = f"{self.base_url}/paper/DOI:{doi}"
        params = {
            "fields": "title,citationCount,referenceCount,year,influentialCitationCount,authors"
        }

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            if response.status_code == 404:
                logger.warning(f"Paper not found: {doi}")
                return None
            response.raise_for_status()
            return response.json()
        except Exception:
            raise
