# User guide

This guide shows you how to use the Multi-Modal Maturity Model (M4) to assess your research software, either from the command line or as a Python package.

## Installation

```bash
pip install multi-modal-maturity-model
```

For local development:
```bash
git clone https://github.com/fair-toolbox/multi-modal-maturity-model.git
cd multi-modal-maturity-model
pip install -e .
```

## Authentication

Some metrics require authentication. Set up your tokens as environment variables:

```bash
export GITHUB_TOKEN="your_github_token"
export GITLAB_TOKEN="your_gitlab_token"  # if using GitLab
```

Or create a `.env` file in your project directory:
```
GITHUB_TOKEN=your_github_token
GITLAB_TOKEN=your_gitlab_token
```

## CLI Usage

The CLI tool `m4` lets you quickly analyze a repository from the command line.

### Basic usage

```bash
m4 owner/repo
```

### With optional parameters

```bash
m4 https://github.com/owner/repo \
  --pmid 12345678 \
  --biotoolsID my_tool \
  --output-dir ./my_results \
  --verbose
```

### CLI Options

- `repository`: GitHub or GitLab repository URL (e.g., `owner/repo` or full URL)
- `--pmid`: PubMed ID for citation metrics (optional)
- `--biotoolsID`: bio.tools identifier (optional)
- `--local-path`: Local repository path for code quality analysis (optional)
- `--output-dir`: Directory to save results (default: `./results`)
- `--verbose, -v`: Enable detailed output


## Package Usage

For programmatic access and custom workflows, use M4 as a Python package.

### Basic Example

```python
from multi_modal_maturity_model.core import MetricsAggregator
from multi_modal_maturity_model.collectors import GitHubCollector

# Initialize with custom settings
aggregator = MetricsAggregator(
    github_token=your_token,
    gitlab_token=your_gitlab_token,
    rate_limit_seconds=2
)

# Analyze multiple repositories
repos = [
    "https://github.com/owner/repo1",
    "https://github.com/owner/repo2"
]

pmids = ["12345678", "87654321"]

results = aggregator.analyze_repositories(
    repo_urls=repos,
    pmids=pmids,
    biotools_ids=["tool1", "tool2"],  # optional
    output_dir="./batch_results"
)
```

### Working with results

Results are saved as CSV files in the output directory:
- `github_metrics.csv` or `gitlab_metrics.csv`: Repository statistics
- `citation_metrics.csv`: Publication and citation data
- `fairness_metrics.csv`: FAIR compliance scores
- `code_quality_metrics.csv`: Static analysis results


TBD

<!--
## Next steps

- Check out the [Metrics](metrics.md) page for details on what each metric measures
- See the `examples/` directory for more usage examples
- Read the [Contributing Guide](contributing.md) to help improve M4
 -->
