"""Command-line interface for the Multi-Modal Maturity Model."""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import click
import yaml

from .pipeline import MaturityPipeline

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="mmmm.%(module)s  -  %(levelname)s  -  %(message)s",
    )
    logging.getLogger("gidgethub").setLevel(logging.ERROR)
    logging.getLogger("gidgetlab").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.ERROR)


@click.group()
@click.version_option(version="0.1.0", prog_name="Multi-Modal Maturity Model")
def main():
    """Command-line interface for the Multi-Modal Maturity Model."""
    pass


@main.command()
@click.argument("repo_url")
@click.option(
    "--biotools",
    "-b",
    "biotools_id",
    help="bio.tools registry identifier",
)
@click.option(
    "--doi",
    "-d",
    "dois",
    multiple=True,
    help="Publication DOI (can specify multiple)",
)
@click.option(
    "--local-repo-path",
    "-l",
    type=click.Path(exists=True),
    help="Local path to repository (skip cloning)",
)
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True),
    help="Custom weights config file path",
)
@click.option(
    "--output", "-o", type=click.Path(), help="Output file path (default: stdout)"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def analyze(
    repo_url: str,
    biotools_id: Optional[str],
    dois: tuple[str, ...],
    local_repo_path: Optional[str],
    config_path: Optional[str],
    output: Optional[str],
    verbose: bool,
) -> None:

    setup_logging(verbose=verbose)

    pipeline = MaturityPipeline()

    try:
        results = asyncio.run(
            pipeline.run(
                repo_url=repo_url,
                repo_path=local_repo_path,
                biotools_id=biotools_id,
                dois=list(dois) if dois else None,
            )
        )

        # output_str = json.dumps(results, indent=2)
        output_str = yaml.dump(results, default_flow_style=False)

        # Write output
        if output:
            Path(output).write_text(output_str)
            click.echo(f"Results written to {output}", err=True)
        else:
            click.echo(output_str)

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
