# src/multi_modal_maturity_model/collectors/fairness.py

"""
FAIR compliance assessment using howfairis as a library.
"""

import logging
from typing import Any
import time

from howfairis import Checker, Repo
from ..utils import URLParser

logger = logging.getLogger(__name__)


class FairnessCollector:
    """
    Collect FAIR compliance metrics using howfairis library.
    """
    
    def __init__(self, rate_limit_seconds: int = 60):
        """
        Parameters
        ----------
        rate_limit_seconds : int
            Seconds to wait between API calls to avoid rate limiting
        """
        self.rate_limit_seconds = rate_limit_seconds
        logger.info("FairnessCollector initialized")
    
    def collect(self, repo_url: str) -> dict[str, Any]:
        """
        Assess FAIR compliance for a single repository.
        
        Parameters
        ----------
        repo_url : str
            GitHub or GitLab repository URL
            
        Returns
        -------
        dict
            Dictionary with FAIR compliance indicators:
            - url: str
            - repository: bool | None
            - license: bool | None
            - registry: bool | None
            - citation: bool | None
            - checklist: bool | None
            
        Raises
        ------
        Exception
            If howfairis assessment fails
        """
        logger.debug(f"Assessing FAIR compliance for: {repo_url}")
        
        try:
            repo = Repo(repo_url)
            # Use howfairis library directly
            checker = Checker(repo)
            checker.check_five_recommendations()
            
            result = {
                "url": repo_url,
                "repository": checker.has_open_repository,
                "license": checker.has_license,
                "registry": checker.has_registry,
                "citation": checker.has_citation,
                "checklist": checker.has_checklist,
            }
            
            logger.info(f"Successfully assessed {repo_url}")
            return result
            
        except Exception as e:
            logger.error(f"Error assessing {repo_url}: {e}")
            return self._empty_result(repo_url)
    
    def collect_batch(self, repo_urls: list[str]) -> list[dict[str, Any]]:
        """
        Assess FAIR compliance for multiple repositories with rate limiting.
        
        Parameters
        ----------
        repo_urls : list[str]
            List of repository URLs
            
        Returns
        -------
        list[dict]
            List of FAIR compliance results
        """
        results = []
        
        for i, url in enumerate(repo_urls):
            logger.info(f"Processing {i+1}/{len(repo_urls)}: {url}")
            
            try:
                result = self.collect(url)
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to assess {url}: {e}")
                results.append(self._empty_result(url))
            
            # Rate limit: wait between requests (except after last one)
            if i < len(repo_urls) - 1:
                logger.debug(f"Rate limiting: waiting {self.rate_limit_seconds}s")
                time.sleep(self.rate_limit_seconds)
        
        return results
    
    def _empty_result(self, repo_url: str) -> dict[str, Any]:
        """
        Return an empty/failed result structure.
        
        Parameters
        ----------
        repo_url : str
            Repository URL
            
        Returns
        -------
        dict
            Result with all None values
        """
        return {
            "url": repo_url,
            "repository": None,
            "license": None,
            "registry": None,
            "citation": None,
            "checklist": None,
        }
    
