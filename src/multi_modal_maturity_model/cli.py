"""Command-line interface for the Multi-Modal Maturity Model."""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click
import yaml

from .config import AppConfig
from .pipeline import MaturityPipeline

logger = logging.getLogger(__name__)


@click.group()
@click.option("-v", "--verbose", count=True, help="Increase verbosity (-v, -vv, -vvv)")
@click.pass_context
def main(ctx: click.Context, verbose: int) -> None:
    """Multi-Modal Maturity Model - Assess research software maturity."""
    # Configure logging
    log_levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = log_levels[min(verbose, len(log_levels) - 1)]
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Store config in context for subcommands
    ctx.ensure_object(dict)


@main.command()
@click.argument("repo_url")
@click.option("--biotools-id", help="bio.tools registry ID")
@click.option(
    "--doi", "dois", multiple=True, help="Publication DOI (can specify multiple)"
)
@click.option(
    "--repo-path",
    type=click.Path(exists=True),
    help="Local repository path (skip cloning)",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True),
    help="Custom config file path",
)
@click.option(
    "--output", "-o", type=click.Path(), help="Output file path (default: stdout)"
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"]),
    default="json",
    help="Output format",
)
@click.pass_context
def analyze(
    ctx: click.Context,
    repo_url: str,
    biotools_id: Optional[str],
    dois: tuple[str, ...],
    repo_path: Optional[str],
    config_path: Optional[str],
    output: Optional[str],
    output_format: str,
) -> None:
    """Analyze a repository and generate maturity profile."""

    # Load configuration
    config = AppConfig.load(
        config_path=Path(config_path) if config_path else None,
    )

    # Create pipeline
    pipeline = MaturityPipeline(config=config)

    # Run analysis
    try:
        results = asyncio.run(
            pipeline.run(
                repo_url=repo_url,
                repo_path=repo_path,
                biotools_id=biotools_id,
                dois=list(dois) if dois else None,
            )
        )

        # Format output
        if output_format == "json":
            output_str = json.dumps(results, indent=2)
        else:
            output_str = yaml.dump(results, default_flow_style=False)

        # Write output
        if output:
            Path(output).write_text(output_str)
            click.echo(f"Results written to {output}", err=True)
        else:
            click.echo(output_str)

    except Exception as e:
        logger.exception("Analysis failed")
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.group()
def config() -> None:
    """Manage configuration settings."""
    pass


@config.command("show")
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True),
    help="Custom config file path",
)
@click.option(
    "--section",
    type=click.Choice(["all", "weights", "metrics", "patterns", "api"]),
    default="all",
)
def config_show(config_path: Optional[str], section: str) -> None:
    """Display current configuration."""
    cfg = AppConfig.load(config_path=Path(config_path) if config_path else None)

    output = {}

    if section in ["all", "weights"]:
        output["weights"] = {
            "dimensions": cfg.weights.dimensions,
            "overall": cfg.weights.overall,
        }

    if section in ["all", "metrics"]:
        output["metrics"] = {
            "count": len(cfg.metrics.metrics),
            "defined": list(cfg.metrics.metrics.keys()),
        }

    if section in ["all", "patterns"]:
        output["patterns"] = {
            "workflow_files": cfg.patterns.workflow_files,
            "distribution_files": cfg.patterns.distribution_files,
            "security_policy_files": cfg.patterns.security_policy_files,
            "security_scanning_files": cfg.patterns.security_scanning_files,
        }

    if section in ["all", "api"]:
        output["api"] = {
            "github_token": "***" if cfg.api.github_token else None,
            "gitlab_token": "***" if cfg.api.gitlab_token else None,
            "altmetric_api_key": "***" if cfg.api.altmetric_api_key else None,
        }

    click.echo(yaml.dump(output, default_flow_style=False))


@config.command("validate")
@click.argument("config_file", type=click.Path(exists=True))
def config_validate(config_file: str) -> None:
    """Validate a configuration file."""
    try:
        cfg = AppConfig.load(config_path=Path(config_file))
        click.echo("✓ Configuration is valid", err=True)

        # Show summary
        click.echo(f"\nDimensions: {len(cfg.weights.dimensions)}")
        click.echo(f"Overall weights: {len(cfg.weights.overall)}")
        click.echo(f"Metrics defined: {len(cfg.metrics.metrics)}")

    except Exception as e:
        click.echo(f"✗ Configuration is invalid: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
