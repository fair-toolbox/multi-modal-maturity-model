"""
Command-line interface for the Multi-Modal Maturity Model.
"""

import click
import json
import logging

from dotenv import load_dotenv
from pathlib import Path

from .assessor import MaturityAssessor
from .models import MaturityProfile
from .weights import validate_weights

from . import __version__

load_dotenv()

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(module)-18s\t%(levelname)-8s\t%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_weights_from_file(weights_path: str) -> dict[str, dict[str, float]]:
    """
    Load and validate custom weights from JSON file.
    """
    try:
        with open(weights_path, "r") as f:
            data = json.load(f)

        # Handle case where weights are nested under "weights" key
        weights = data.get("weights", data)

        validate_weights(weights)
        return weights

    except FileNotFoundError:
        raise click.ClickException(f"Weights file not found: {weights_path}")
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON in weights file: {e}")
    except ValueError as e:
        raise click.ClickException(f"Invalid weights: {e}")


def format_output(profile: MaturityProfile, format_type: str) -> str:
    """
    Format MaturityProfile for output (JSON, pretty, or YAML).
    """
    if format_type == "json":
        return profile.to_json(indent=2)

    elif format_type == "pretty":
        lines = []
        lines.append("=" * 60)
        lines.append("MATURITY ASSESSMENT REPORT")
        lines.append("=" * 60)
        lines.append("")

        # Overall Score
        if profile.overall_score:
            lines.append(f"Overall Score: {profile.overall_score.score:.2f}")
            lines.append("")

        # Dimension Scores
        dimensions = [
            profile.compatibility,
            profile.fairness,
            profile.maintainability,
            profile.sustainability,
            profile.security,
            profile.scientific_impact,
        ]

        for dim in dimensions:
            if dim and dim.score is not None:
                lines.append(f"{dim.name.upper()}: {dim.score:.2f}")
                if dim.details:
                    for key, value in dim.details.items():
                        if value is not None:
                            lines.append(f"  • {key}: {value}")
                lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    else:
        raise click.ClickException(f"Unknown format: {format_type}")


def write_output(content: str, output_path: str | None) -> None:
    """Write output to file or stdout."""
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(content)
        click.echo(f"✓ Results written to: {output_path}", err=True)
    else:
        click.echo(content)


@click.group()
@click.version_option(version=__version__, prog_name="m4")
def cli():
    """
    Multi-Modal Maturity Model (M4) - Assessment tool for research software.

    Evaluates research software across multiple dimensions:
    compatibility, fairness, maintainability, sustainability,
    security, and scientific impact.
    """
    pass


@cli.command()
@click.option(
    "--repo",
    "-r",
    "repo_url",
    required=True,
    help="Repository URL (e.g., https://github.com/owner/repo)",
)
@click.option(
    "--biotools",
    "-b",
    "biotools_id",
    help="bio.tools identifier (e.g., blast)",
)
@click.option(
    "--pmid",
    "-p",
    help="PubMed ID for citation metrics",
)
@click.option(
    "--doi",
    "-d",
    help="DOI for citation metrics (alternative to PMID)",
)
@click.option(
    "--local-path",
    "-l",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Local path to repository (skips cloning)",
)
@click.option(
    "--github-token",
    envvar="GITHUB_TOKEN",
    help="GitHub API token (or set GITHUB_TOKEN env var)",
)
@click.option(
    "--gitlab-token",
    envvar="GITLAB_TOKEN",
    help="GitLab API token (or set GITLAB_TOKEN env var)",
)
@click.option(
    "--no-code-quality",
    is_flag=True,
    help="Skip code quality analysis (faster, no cloning needed)",
)
@click.option(
    "--weights",
    "-w",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to custom weights JSON file",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path (default: stdout)",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "pretty"], case_sensitive=False),
    default="json",
    help="Output format (default: json)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def assess(
    repo_url: str,
    biotools_id: str | None,
    pmid: str | None,
    doi: str | None,
    local_path: str | None,
    github_token: str | None,
    gitlab_token: str | None,
    no_code_quality: bool,
    weights: str | None,
    output: str | None,
    output_format: str,
    verbose: bool,
):
    """
    Assess maturity of a single research software tool.

    Example:
        m4 assess --repo https://github.com/owner/repo --biotools blast
    """
    setup_logging(verbose)

    if not github_token and not gitlab_token:
        raise click.ClickException(
            "At least one API token is required. "
            "Provide --github-token, --gitlab-token, or set GITHUB_TOKEN/GITLAB_TOKEN environment variables."
        )

    custom_weights = None
    if weights:
        custom_weights = load_weights_from_file(weights)
        click.echo(f"✓ Loaded custom weights from: {weights}", err=True)

    try:
        # Initialize assessor
        assessor = MaturityAssessor(
            github_token=github_token,
            gitlab_token=gitlab_token,
            weights=custom_weights,
        )

        # Run assessment
        click.echo("🔍 Starting maturity assessment...", err=True)
        profile = assessor.assess(
            biotools_id=biotools_id,
            repo_url=repo_url,
            repo_path=local_path,
            pmid=pmid,
            doi=doi,
            include_code_quality=not no_code_quality,
        )

        # Format and output results
        formatted_output = format_output(profile, output_format)
        write_output(formatted_output, output)

        if not output:
            click.echo("", err=True)
        click.echo("✅ Assessment complete!", err=True)

    except Exception as e:
        logger.exception("Assessment failed")
        raise click.ClickException(str(e))


def main():
    cli()


if __name__ == "__main__":
    main()
