"""
EDAM Ontology Data Loader

Loads pre-bundled EDAM ontology format data.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Bundled data
PACKAGE_DATA_DIR = Path(__file__).parent / "data"
BUNDLED_CACHE_FILE = PACKAGE_DATA_DIR / "edam_format.json"


class EDAMCache:
    """Loads and provides access to bundled EDAM format ontology."""

    def __init__(self):
        self._leaf_node_uris: set[str] | None = None
        self._all_terms: dict[str, dict] | None = None
        self._has_children: set[str] | None = None

    def _load_bundled_data(self) -> dict:
        """Load EDAM data from bundled package data."""
        if not BUNDLED_CACHE_FILE.exists():
            raise FileNotFoundError(
                f"Bundled EDAM data not found at {BUNDLED_CACHE_FILE}. "
                f"Package may be corrupted or data file was not included in distribution."
            )

        logger.debug(f"Loading EDAM ontology from bundled data: {BUNDLED_CACHE_FILE}")
        with open(BUNDLED_CACHE_FILE, "r") as f:
            return json.load(f)

    def _ensure_loaded(self):
        """Ensure EDAM data is loaded into memory."""
        # If already loaded
        if self._leaf_node_uris is not None:
            return

        try:
            cache_data = self._load_bundled_data()
            self._all_terms = cache_data["all_terms"]
            self._has_children = set(cache_data["has_children"])
            self._leaf_node_uris = set(cache_data["leaf_node_uris"])

            stats = cache_data.get("stats", {})
            logger.info(
                f"Loaded EDAM ontology: {stats.get('total_terms', len(self._all_terms))} terms "
                f"({stats.get('leaf_nodes', len(self._leaf_node_uris))} leaf nodes)"
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                "EDAM ontology data file is missing from package installation. "
                "Please reinstall the package or contact the maintainers."
            ) from e
        except (json.JSONDecodeError, KeyError) as e:
            raise RuntimeError(
                f"EDAM ontology data file is corrupted: {e}. "
                "Please reinstall the package."
            ) from e

    def get_leaf_node_uris(self) -> set[str]:
        """
        Get the set of EDAM format URIs that are leaf nodes.

        Returns:
            Set of URIs for leaf node terms
        """
        self._ensure_loaded()
        return self._leaf_node_uris.copy()

    def is_leaf_node(self, uri: str) -> bool:
        """
        Check if a given URI is a leaf node.

        Args:
            uri: EDAM format URI to check

        Returns:
            True if URI is a leaf node, False otherwise
        """
        self._ensure_loaded()
        return uri in self._leaf_node_uris

    def get_term_info(self, uri: str) -> dict | None:
        """
        Get information about a specific EDAM term.

        Args:
            uri: EDAM format URI

        Returns:
            Dict with term info (uri, term, num_children) or None if not found
        """
        self._ensure_loaded()
        return self._all_terms.get(uri)

    def get_all_terms(self) -> dict[str, dict]:
        """
        Get all EDAM terms.

        Returns:
            Dict mapping URIs to term info
        """
        self._ensure_loaded()
        return self._all_terms.copy()

    def get_stats(self) -> dict:
        """
        Get statistics about the loaded EDAM ontology.

        Returns:
            Dict with statistics (total_terms, terms_with_children, leaf_nodes)
        """
        self._ensure_loaded()
        return {
            "total_terms": len(self._all_terms),
            "terms_with_children": len(self._has_children),
            "leaf_nodes": len(self._leaf_node_uris),
        }
