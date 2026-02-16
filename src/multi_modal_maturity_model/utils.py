"""Utility functions for URL parsing and file operations."""

from urllib.parse import urlparse


class URLParser:
    """Parse and normalize repository URLs."""
    
    @staticmethod
    def to_owner_repo(url: str) -> str:
        """
        Convert various URL formats to owner/repo format.
        
        Parameters
        ----------
        url : str
            Repository URL in various formats:
            - https://github.com/owner/repo
            - http://github.com/owner/repo
            - git@github.com:owner/repo.git
            - owner/repo
            
        Returns
        -------
        str
            Normalized "owner/repo" string
            
        Examples
        --------
        >>> URLParser.to_owner_repo("https://github.com/fair-toolbox/bridge")
        'fair-toolbox/bridge'
        >>> URLParser.to_owner_repo("git@github.com:fair-toolbox/bridge.git")
        'fair-toolbox/bridge'
        """
        url = url.strip()
        
        # Handle HTTP(S) URLs
        if url.startswith(("http://", "https://")):
            parsed = urlparse(url)
            parts = [x for x in parsed.path.strip("/").split("/") if x]
            return "/".join(parts[:2])
        
        # Handle git@github.com: format
        if url.startswith("git@github.com:"):
            path = url.split(":", 1)[1].rstrip("/").removesuffix(".git")
            return "/".join(path.split("/")[:2])
        
        # Assume already in owner/repo format
        return "/".join(url.strip("/").removesuffix(".git").split("/")[:2])
    