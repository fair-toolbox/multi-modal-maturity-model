#!/usr/bin/env python3
"""
Script to fetch and bundle EDAM format ontology data with the package.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import requests

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

EDAM_API_URL = "https://bio.tools/api/o/edam_format"
EDAM_VERSION = "latest"
OUTPUT_FILE = (
    project_root / "src" / "multi_modal_maturity_model" / "data" / "edam_format.json"
)


def parse_ontology_tree(node: dict, all_terms: dict, has_children: set, depth: int = 0):
    """
    Recursively parse the EDAM tree and collect all unique terms.
    """
    if not node or not isinstance(node, dict):
        return

    # Extract node information
    uri = node.get("data", {}).get("uri") if node.get("data") else None
    term = node.get("text", "Unknown")
    children = node.get("children", [])

    if not uri:
        return

    # Store term information
    if uri not in all_terms or len(children) > all_terms[uri]["num_children"]:
        all_terms[uri] = {"uri": uri, "term": term, "num_children": len(children)}

    # Track nodes with children (non-leaf nodes)
    if children:
        has_children.add(uri)
        for child in children:
            parse_ontology_tree(child, all_terms, has_children, depth + 1)


def fetch_and_process_edam():
    """Fetch EDAM ontology from API and process it."""
    print(f"Fetching EDAM format ontology from {EDAM_API_URL}...")

    try:
        response = requests.get(EDAM_API_URL, timeout=30)
        response.raise_for_status()
        edam_data = response.json()
    except requests.RequestException as e:
        print(f"ERROR: Failed to fetch EDAM data: {e}")
        sys.exit(1)

    all_terms = {}
    has_children = set()

    # Parse the tree
    root_node = edam_data.get("data")
    if not root_node:
        print("ERROR: Could not find 'data' key in EDAM response")
        sys.exit(1)

    parse_ontology_tree(root_node, all_terms, has_children)

    leaf_nodes = [uri for uri in all_terms.keys() if uri not in has_children]

    print(f"\nEDAM format ontology processing complete:")
    print(f"  Total terms: {len(all_terms)}")
    print(f"  Terms with children: {len(has_children)}")
    print(f"  Leaf nodes: {len(leaf_nodes)}")

    # Prepare cache data
    cache_data = {
        "version": EDAM_VERSION,
        "source": EDAM_API_URL,
        "all_terms": all_terms,
        "has_children": list(has_children),
        "leaf_node_uris": leaf_nodes,
    }

    return cache_data


def save_cache_data(cache_data: dict):
    """Save cache data."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nSaving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(cache_data, f, indent=2)


def main():
    """Main entry point."""
    print("=" * 60)
    print("EDAM Update")
    print("=" * 60)
    print()

    cache_data = fetch_and_process_edam()

    save_cache_data(cache_data)

    print()
    print("✓ Successfully updated bundled EDAM data!")


if __name__ == "__main__":
    main()
