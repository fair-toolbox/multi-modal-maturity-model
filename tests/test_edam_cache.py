"""Tests for EDAM data loader functionality."""

import pytest
from multi_modal_maturity_model.edam import (
    EDAMCache,
    BUNDLED_CACHE_FILE,
)


class TestEDAMCache:
    """Test EDAM data loader functionality."""

    edam_cache = EDAMCache()

    def test_bundled_file_exists(self):
        """Test that bundled EDAM data file exists."""
        assert BUNDLED_CACHE_FILE.exists(), "Bundled EDAM data file should exist"

    def test_get_leaf_node_uris(self):
        """Test getting leaf node URIs."""
        leaf_nodes = self.edam_cache.get_leaf_node_uris()

        assert isinstance(leaf_nodes, set)
        assert len(leaf_nodes) > 0

        # All URIs should be strings and properly formatted
        for uri in list(leaf_nodes)[:5]:
            assert isinstance(uri, str)
            assert uri.startswith("http://edamontology.org/")

    def test_is_leaf_node(self):
        """Test checking if a URI is a leaf node."""
        leaf_nodes = self.edam_cache.get_leaf_node_uris()

        # Pick a known leaf node
        if leaf_nodes:
            sample_leaf = next(iter(leaf_nodes))
            assert self.edam_cache.is_leaf_node(sample_leaf) is True

        # Test with a non-existent URI
        assert (
            self.edam_cache.is_leaf_node("http://edamontology.org/format_99999")
            is False
        )

    def test_get_term_info(self):
        """Test getting term information."""
        leaf_nodes = self.edam_cache.get_leaf_node_uris()

        if leaf_nodes:
            sample_uri = next(iter(leaf_nodes))
            info = self.edam_cache.get_term_info(sample_uri)

            assert info is not None
            assert "uri" in info
            assert "term" in info
            assert "num_children" in info
            assert info["uri"] == sample_uri
            assert isinstance(info["term"], str)
            assert isinstance(info["num_children"], int)

    def test_get_all_terms(self):
        """Test getting all terms."""
        all_terms = self.edam_cache.get_all_terms()

        assert isinstance(all_terms, dict)
        assert len(all_terms) > 0

        # Check structure of a term
        sample_uri = next(iter(all_terms.keys()))
        term_info = all_terms[sample_uri]
        assert "uri" in term_info
        assert "term" in term_info
        assert "num_children" in term_info

    def test_get_stats(self):
        """Test getting statistics."""
        stats = self.edam_cache.get_stats()

        assert isinstance(stats, dict)
        assert "total_terms" in stats
        assert "terms_with_children" in stats
        assert "leaf_nodes" in stats

        # Verify math adds up
        assert (
            stats["total_terms"] == stats["terms_with_children"] + stats["leaf_nodes"]
        )

        # Reasonable ranges
        assert stats["total_terms"] > 500
        assert stats["leaf_nodes"] > 400

    def test_data_consistency(self):
        """Test that data is internally consistent."""
        leaf_nodes = self.edam_cache.get_leaf_node_uris()
        all_terms = self.edam_cache.get_all_terms()
        stats = self.edam_cache.get_stats()

        # Leaf nodes should be subset of all terms
        for uri in leaf_nodes:
            assert uri in all_terms
            # Leaf nodes should have 0 children
            assert all_terms[uri]["num_children"] == 0

        # Stats should match actual data
        assert len(all_terms) == stats["total_terms"]
        assert len(leaf_nodes) == stats["leaf_nodes"]


class TestEDAMCacheClass:
    """Test EDAMCache class directly."""

    def test_singleton_behavior(self):
        """Test that multiple instances share the same loaded data."""
        cache1 = EDAMCache()
        cache2 = EDAMCache()

        # Get data from both instances
        leaf1 = cache1.get_leaf_node_uris()
        leaf2 = cache2.get_leaf_node_uris()

        # Should return equivalent data
        assert leaf1 == leaf2

    def test_lazy_loading(self):
        """Test that data is only loaded when first accessed."""
        cache = EDAMCache()

        # Initially, data should not be loaded
        assert cache._leaf_node_uris is None

        # Access data
        _ = cache.get_leaf_node_uris()

        # Now data should be loaded
        assert cache._leaf_node_uris is not None

    def test_memory_caching(self):
        """Test that data stays in memory after first load."""
        cache = EDAMCache()

        # First access
        leaf1 = cache.get_leaf_node_uris()
        internal_ref1 = id(cache._leaf_node_uris)

        # Second access
        leaf2 = cache.get_leaf_node_uris()
        internal_ref2 = id(cache._leaf_node_uris)

        # Should be same object in memory
        assert internal_ref1 == internal_ref2
        assert leaf1 == leaf2
