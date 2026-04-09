#!/usr/bin/env python3
"""Command-line interface for Multi-Modal Maturity Model (M4)"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from . import MaturityAssessor, __version__


def load_input_config(config_path: str) -> dict:
    """Load CLI defaults from a JSON config file."""
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    if path.suffix.lower() != ".json":
        raise ValueError("Unsupported config file format. Use .json")

    with path.open() as handle:
        config = json.load(handle)

    if config is None:
        return {}

    if not isinstance(config, dict):
        raise ValueError("Config file must contain a top-level object/mapping")

    return config


def build_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        description="Multi-Modal Maturity Model (M4) - Assess maturity of research software",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
              # Repository URL
              m4 https://github.com/owner/repo
              m4 https://gitlab.com/group/subgroup/project

              # Full assessment with all data sources
              m4 https://github.com/owner/repo --pmid 12345678 --biotools-id blast

              # Use local repository (no cloning)
              m4 https://github.com/owner/repo --local-path /path/to/repo

                # Read defaults from a JSON config file
              m4 --input config.json

              # Skip code quality analysis (faster, no cloning)
              m4 https://github.com/owner/repo --no-code-quality

            Environment Variables:
              GITHUB_TOKEN    GitHub API token for authenticated requests
              GITLAB_TOKEN    GitLab API token for authenticated requests
        """,
    )
    parser.add_argument(
        "repository",
        nargs="?",
        default=None,
        help="Repository URL",
    )
    parser.add_argument(
        "--input",
        help="Path to a JSON config file with CLI defaults",
        default=None,
    )
    parser.add_argument(
        "--pmid",
        help="PubMed ID for citation metrics",
        default=None,
    )
    parser.add_argument(
        "--biotoolsID",
        help="bio.tools identifier",
        default=None,
        dest="biotools_id",
    )
    parser.add_argument(
        "--local-path",
        help="Local path to repository (skips cloning)",
        default=None,
        dest="local_path",
    )
    parser.add_argument(
        "--output-dir",
        help="Output directory for results (default: ./results)",
        default="./results",
        dest="output_dir",
    )
    parser.add_argument(
        "--no-code-quality",
        action="store_true",
        help="Skip code quality analysis (faster, no repository cloning)",
        dest="no_code_quality",
    )
    parser.add_argument(
        "--max-citations",
        type=int,
        help="Maximum citations in corpus for normalization (default: 1000)",
        default=1000,
        dest="max_citations",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output with detailed metrics",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def normalize_config_keys(
    parser: argparse.ArgumentParser, config: dict[str, object]
) -> dict[str, object]:
    """Map config-file keys onto argparse destination names."""
    key_map: dict[str, str] = {}

    for action in parser._actions:
        if action.dest == argparse.SUPPRESS:
            continue

        key_map[action.dest] = action.dest
        for option in action.option_strings:
            normalized_option = option.lstrip("-").replace("-", "_")
            key_map[normalized_option] = action.dest

    normalized: dict[str, object] = {}
    unknown_keys: list[str] = []
    for key, value in config.items():
        normalized_key = key.replace("-", "_")
        dest = key_map.get(normalized_key)
        if dest is None:
            unknown_keys.append(key)
            continue
        normalized[dest] = value

    if unknown_keys:
        valid_keys = ", ".join(sorted(key_map))
        unknown = ", ".join(sorted(unknown_keys))
        raise ValueError(f"Unknown config key(s): {unknown}. Valid keys: {valid_keys}")

    return normalized


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )


def print_results(profile, verbose: bool = False) -> None:
    """Print assessment results to console in a nice format."""
    print("\n" + "=" * 70)
    print("MATURITY ASSESSMENT RESULTS")
    print("=" * 70)
    print(f"\n{'Overall Maturity Score:':<30} {profile.overall_score:>6.1%}")
    print("\n" + "-" * 70)
    print("Dimension Breakdown:")
    print("-" * 70)

    dimensions = [
        ("Compatibility", profile.compatibility),
        ("FAIRness", profile.fairness),
        ("Maintainability", profile.maintainability),
        ("Sustainability", profile.sustainability),
        ("Security", profile.security),
        ("Scientific Impact", profile.scientific_impact),
    ]

    for name, dim in dimensions:
        if dim.score is None:
            # Dimension not available
            bar = "─" * 20
            print(f"  {name:<20} {bar} {'N/A':>6}")
        else:
            # Create visual bar
            bar_length = int(dim.score * 20)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            print(f"  {name:<20} {bar} {dim.score:>6.1%}")

    if verbose and any(dim.details for _, dim in dimensions):
        print("\n" + "-" * 70)
        print("Detailed Metrics:")
        print("-" * 70)
        for name, dim in dimensions:
            if dim.details:
                print(f"\n  {name}:")
                for key, value in dim.details.items():
                    if isinstance(value, float):
                        print(f"    • {key}: {value:.2f}")
                    else:
                        print(f"    • {key}: {value}")

    print("\n" + "=" * 70)


def save_results(profile, output_dir: str, repository: str) -> None:
    """Save assessment results to JSON file."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create safe filename from repository name
    safe_repo_name = (
        repository.replace("/", "_").replace("https://", "").replace("http://", "")
    )
    output_file = output_path / f"{safe_repo_name}_maturity_profile.json"

    # Convert dataclass to dict
    profile_dict = {
        "overall_score": profile.overall_score,
        "dimensions": {
            "compatibility": {
                "score": profile.compatibility.score,
                "details": profile.compatibility.details,
            },
            "fairness": {
                "score": profile.fairness.score,
                "details": profile.fairness.details,
            },
            "maintainability": {
                "score": profile.maintainability.score,
                "details": profile.maintainability.details,
            },
            "sustainability": {
                "score": profile.sustainability.score,
                "details": profile.sustainability.details,
            },
            "security": {
                "score": profile.security.score,
                "details": profile.security.details,
            },
            "scientific_impact": {
                "score": profile.scientific_impact.score,
                "details": profile.scientific_impact.details,
            },
        },
    }

    with open(output_file, "w") as f:
        json.dump(profile_dict, f, indent=2)

    print(f"\n✓ Results saved to: {output_file}")


def main():
    """Main entry point for the CLI."""
    # Load environment variables from .env file if it exists
    load_dotenv()

    bootstrap_parser = argparse.ArgumentParser(add_help=False)
    bootstrap_parser.add_argument("--input", default=None)
    bootstrap_args, _ = bootstrap_parser.parse_known_args()

    parser = build_parser()
    if bootstrap_args.input:
        try:
            config = load_input_config(bootstrap_args.input)
            parser.set_defaults(**normalize_config_keys(parser, config))
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            parser.error(str(exc))

    args = parser.parse_args()
    if not args.repository:
        parser.error("the following arguments are required: repository")

    # Setup logging
    setup_logging(args.verbose)

    # Print header
    print(f"\n{'=' * 70}")
    print(f"M4 - Multi-Modal Maturity Model v{__version__}")
    print(f"{'=' * 70}\n")
    print(f"Repository: {args.repository}")

    if args.biotools_id:
        print(f"bio.tools ID: {args.biotools_id}")
    if args.pmid:
        print(f"PubMed ID: {args.pmid}")
    if args.local_path:
        print(f"Local path: {args.local_path}")

    print(f"\nOptions:")
    print(f"  • Code quality analysis: {'No' if args.no_code_quality else 'Yes'}")

    # Get API tokens from environment
    github_token = os.environ.get("GITHUB_TOKEN")
    gitlab_token = os.environ.get("GITLAB_TOKEN")

    try:
        # Initialize assessor
        assessor = MaturityAssessor(
            github_token=github_token,
            gitlab_token=gitlab_token,
            max_citations_corpus=args.max_citations,
        )

        # Run assessment
        print(f"\n{'─' * 70}")
        print("Starting assessment...")
        print(f"{'─' * 70}\n")

        profile = assessor.assess(
            biotools_id=args.biotools_id,
            repo_url=args.repository,
            repo_path=args.local_path,
            pmid=args.pmid,
            collect_code_quality=not args.no_code_quality,
        )

        print_results(profile, verbose=args.verbose)

        save_results(profile, args.output_dir, args.repository)

        print("\n✓ Assessment complete!\n")
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠ Assessment interrupted by user")
        return 130

    except Exception as e:
        logging.error(f"Assessment failed: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
