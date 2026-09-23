# User Guide

This guide shows how to install and use the Multi-Modal Maturity Model (MMMM) to analyze research software repositories.

## Installation

Requires Python 3.11+.

```bash
pip install git+https://github.com/fair-toolbox/multi-modal-maturity-model.git
```

This installs both the `maturity-model` command-line tool and the `multi_modal_maturity_model` Python package.

## API Tokens

M4 talks to several external services. GitHub and GitLab require API tokens; set them in the environment or a `.env` file in your working directory:

```dotenv
GITHUB_TOKEN=ghp_...
GITLAB_TOKEN=glpat-...
ALTMETRIC_TOKEN=...
```

!!! note
    A GitHub token is required to analyze GitHub repositories, and a GitLab token to analyze GitLab repositories. `ALTMETRIC_TOKEN` is optional; without it, Altmetric attention scores are skipped.

## Command-Line Usage

Analyze a repository and print a summary to the terminal:

```bash
maturity-model analyze https://github.com/user/repo
```

Save the full results as JSON:

```bash
maturity-model analyze https://github.com/user/repo -o results.json
```

### Options

| Option | Description |
|---|---|
| `--biotools, -b` | bio.tools registry identifier of the tool |
| `--doi` | Publication DOI (can be specified multiple times) |
| `--local-repo-path, -l` | Path to a local checkout (skips cloning) |
| `--weights, -w` | Path to a custom weights configuration file |
| `--output, -o` | Output file path (default: print summary to stdout) |
| `--verbose, -v` | Enable verbose logging |

Example with optional identifiers:

```bash
maturity-model analyze https://github.com/user/repo \
  --biotools my-tool \
  --doi 10.1000/example \
  --weights my-weights.yaml \
  --output results.json
```

### Output

The terminal summary shows the overall score and the score of each dimension, with the contribution of every metric:

```
==================================================
Maturity Analysis Results:
==================================================

OVERALL SCORE: 0.62

FAIRNESS: 0.80
    Metric                     |       Value  |  Contribution
  • license                     |         N/A  |  0.00
  • repository                  |         1.00  |  0.30
  ...
```

With `--output`, a JSON file is written containing the overall score, per-dimension scores, and for each metric its raw value, normalized value, effective weight and contribution.

## How Scoring Works

1. **Extraction** — raw values are collected for every metric from the data sources (see [Dimensions and Metrics](maturity_model.md)).
2. **Normalization** — numeric metrics are scaled to $[0, 1]$ (e.g., clamped or log-scaled), with "lower is better" metrics inverted. Boolean metrics map to 0 or 1.
3. **Dimension scores** — a weighted average of the available metrics per dimension. Weights are renormalized over the available metrics, so a missing metric does not penalize the score.
4. **Overall score** — a weighted average of the dimension scores, again renormalized if a dimension could not be computed.

Weights are fully configurable; see [Configuration](configuration.md).

## Next Steps

- [Dimensions and Metrics](maturity_model.md) — what M4 measures and where the data comes from
- [Configuration](configuration.md) — custom weights, metrics and file patterns
