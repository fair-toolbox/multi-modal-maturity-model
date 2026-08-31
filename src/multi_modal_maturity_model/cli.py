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


def format_output(results: dict) -> str:
    lines = []
    lines.append("=" * 50)
    lines.append("Maturity Analysis Results:")
    lines.append("=" * 50)
    lines.append("")

    if "overall_score" in results and results["overall_score"] is not None:
        lines.append(f"OVERALL SCORE: {results['overall_score']:.2f}")
    else:
        lines.append("Overall Score: N/A")
    lines.append("")

    for dimension in results.get("dimensions", []):
        name = dimension["dimension"].upper().replace("_", " ")
        lines.append(f"{name}: {dimension['score']:.2f}")

        lines.append(f"    {'Metric':<25}  |  {'Value':>10}  |  {'Contribution'}")

        for metric in dimension.get("metrics", []):
            raw = metric["raw_value"]
            raw_str = f"{raw:.2f}" if isinstance(raw, (int, float)) else "N/A"
            lines.append(
                f"  • {metric['metric']:<25}  |  {raw_str:>10}  |  {metric['contribution']:.2f}"
            )

        lines.append("")

    lines.append("=" * 50)
    return "\n".join(lines)


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
    "--weights",
    "-w",
    "weights_path",
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
    weights_path: Optional[str],
    output: Optional[str],
    verbose: bool,
) -> None:

    setup_logging(verbose=verbose)

    pipeline = MaturityPipeline(weights_path=weights_path)

    try:
        results = asyncio.run(
            pipeline.run(
                repo_url=repo_url,
                repo_path=local_repo_path,
                biotools_id=biotools_id,
                dois=list(dois) if dois else None,
            )
        )

        if output:
            output_str = json.dumps(results, indent=4)
            Path(output).write_text(output_str)
            click.echo(f"Results written to {output}", err=True)
        else:
            click.echo(format_output(results))

    except Exception as e:
        logger.exception("Analysis failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
