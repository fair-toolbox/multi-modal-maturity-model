#!/usr/bin/env python3
"""Command-line interface for Multi-Modal Maturity Model (M4)"""

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

from . import MaturityAssessor, __version__


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

    parser = argparse.ArgumentParser(
        description="Multi-Modal Maturity Model (M4) - Assess maturity of research software",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # GitHub repository (short format)
  m4 owner/repo --platform=github

  # GitLab repository (short format)
  m4 group/project --platform=gitlab

  # Repository URL (no flag needed)
  m4 https://github.com/owner/repo
  m4 https://gitlab.com/group/subgroup/project

  # Full assessment with all data sources
  m4 owner/repo --platform=github --pmid 12345678 --biotools-id blast

  # Use local repository (no cloning)
  m4 owner/repo --platform=github --local-path /path/to/repo

  # Skip code quality analysis (faster, no cloning)
  m4 owner/repo --platform=github --no-code-quality

Environment Variables:
  GITHUB_TOKEN    GitHub API token for authenticated requests
  GITLAB_TOKEN    GitLab API token for authenticated requests
        """,
    )
    parser.add_argument(
        "repository",
        help="Repository identifier (e.g., owner/repo or full URL)",
    )

    parser.add_argument(
        "--platform",
        choices=["github", "gitlab"],
        help="Repository platform (required for short format like owner/repo)",
        default=None,
    )

    parser.add_argument(
        "--pmid",
        help="PubMed ID for citation metrics",
        default=None,
    )
    parser.add_argument(
        "--biotools-id",
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

    args = parser.parse_args()

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
    print(f"  • FAIR compliance: {'No' if args.no_fair else 'Yes'}")

    # Validate platform usage
    platform = args.platform
    is_url = args.repository.startswith(("http://", "https://", "git@"))

    if platform and is_url:
        print("\n⚠ Warning: --platform flag ignored when using URL format")
        platform = None
    elif not platform and not is_url:
        print("\n⚠ Error: Short format (owner/repo) requires --platform flag")
        print("  Use --platform=github for GitHub repositories")
        print("  Use --platform=gitlab for GitLab repositories")
        print("  Or provide a full URL instead\n")
        return 1

    # Get API tokens from environment
    github_token = os.environ.get("GITHUB_TOKEN")
    gitlab_token = os.environ.get("GITLAB_TOKEN")

    if not github_token and (
        platform == "github" or (is_url and "github" in args.repository.lower())
    ):
        print("\n⚠ Warning: No GitHub token provided. API rate limits may apply.")
        print("  Set GITHUB_TOKEN environment variable or use --github-token")

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
            platform=platform,
            collect_code_quality=not args.no_code_quality,
            collect_fair=not args.no_fair,
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
