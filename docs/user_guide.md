# User guide

This guide shows you how to use the Multi-Modal Maturity Model (M4) to assess your research software, either from the command line or as a Python package.

## Installation

With poetry:

```bash
poetry install
```

## Authentication

Copy the example environment file:

```bash
cp .env.example .env
```

Add your token(s) to `.env`:

```bash
GITHUB_TOKEN=your_github_token
GITLAB_TOKEN=your_gitlab_token
```

## CLI Usage

The CLI tool `m4` lets you quickly analyze a repository from the command line.

### Basic usage

```bash
poetry run m4 owner/repo --platform=github
```

or

```bash
poetry run m4 https://github.com/owner/repo
```

### Complete assessment with all data sources

```bash
poetry run m4 https://github.com/owner/repo \
  --pmid 12345678 \
  --biotoolsID my_tool \
```

### CLI Options

- `repository`: GitHub or GitLab repository URL (e.g., `owner/repo` or full URL)
- `--platform`: If not full URL, platform needs to be provided (_github_ or _gitlab_)
- `--local-path`: Local repository path for code quality analysis (optional, skips cloning)
- `--pmid`: PubMed ID for citation metrics (optional)
- `--biotools-id`: bio.tools identifier (optional)
- `--output-dir`: Directory to save results (default: `./results`)
- `--verbose, -v`: Enable detailed output


#### Analysis Control

- `--no-code-quality` - Skip code quality analysis (faster, no cloning)
- `--no-fair` - Skip FAIR compliance assessment


#### Authentication

- `--github-token TOKEN` - GitHub API token (or use `GITHUB_TOKEN` env var)
- `--gitlab-token TOKEN` - GitLab API token (or use `GITLAB_TOKEN` env var)


#### Configuration

- `--output-dir DIR` - Output directory for results (default: `./results`)
- `--max-citations NUM` - Max citations for normalization (default: 1000)
- `--verbose, -v` - Enable detailed output with metrics breakdown
- `--version` - Show version and exit
- `--help, -h` - Show help message

## Package Usage (TDB)

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

TBD

<!--
## Next steps

- Check out the [Metrics](metrics.md) page for details on what each metric measures
- See the `examples/` directory for more usage examples
- Read the [Contributing Guide](contributing.md) to help improve M4
 -->
