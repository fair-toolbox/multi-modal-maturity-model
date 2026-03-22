import requests
from typing import Any


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
        self._session = requests.Session()

    def get_paper_by_doi(self, doi: str) -> dict[str, Any] | None:
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
            response = self._session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 404:
                print(f"Paper not found: {doi}")
                return None
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching paper {doi}: {e}")
            return None
