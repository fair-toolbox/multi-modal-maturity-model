# Configuration

MMMM is configured through YAML files. Sensible defaults ship with the package and are used automatically; everything can be overridden.

The three configuration files are:

| File | Purpose |
|---|---|
| `weights.yaml` | Metric weights per dimension and dimension weights for the overall score |
| `metrics.yaml` | Metric definitions: type, extraction method, sources and normalization |
| `patterns.yaml` | File patterns used by pattern-based metrics |

The defaults live in `src/mmmm/config/default/` of the repository, and an example weights file is provided at [`config/example_weights.yaml`](https://github.com/fair-toolbox/multi-modal-maturity-model/blob/main/config/example_weights.yaml).

## API Tokens

Runtime settings (API tokens) are read from environment variables or a `.env` file:

| Variable | Required | Used for |
|---|---|---|
| `GITHUB_TOKEN` | For GitHub repositories | GitHub API access |
| `GITLAB_TOKEN` | For GitLab repositories | GitLab API access |
| `ALTMETRIC_TOKEN` | No | Altmetric Attention Score |

## Custom Weights

Pass a custom weights file to weight dimensions and metrics to your needs:

```bash
mmmm analyze https://github.com/user/repo --weights my-weights.yaml
```

```python
pipeline = MaturityPipeline(weights_path="my-weights.yaml")
```

A weights file has two sections — `dimensions` (metric weights within each dimension) and `overall` (dimension weights for the overall score):

```yaml
dimensions:
  maintainability:
    nloc_per_file: 0.30
    avg_ccn: 0.40
    duplicate_rate: 0.30

  sustainability:
    avg_issue_close_time_days: 0.40
    num_open_issues: 0.30
    days_since_last_commit: 0.20
    inverse_simpson_index: 0.10

  # ... other dimensions

overall:
  compatibility: 0.20
  fairness: 0.20
  maintainability: 0.20
  scientific_impact: 0.10
  security: 0.10
  sustainability: 0.20
```

Rules:

- **Metric names must match** those defined in the default `metrics.yaml` (see [Dimensions and Metrics](maturity_model.md)); unknown metrics are rejected with an error.
- **Weights are relative** — they do not need to sum to 1; they are normalized at scoring time.
- **Missing metrics are skipped**, and the remaining weights are renormalized, so unavailable data does not penalize a score.

## Metric Definitions (`metrics.yaml`)

Each metric entry defines its type, how it is extracted, and how it is normalized:

```yaml
metrics:
  star_count:
    type: numeric
    description: "Number of repository stars indicating popularity"
    extraction:
      method: direct
      sources:
        github:
          path: "repository.stargazers_count"
        gitlab:
          path: "repository.star_count"
    normalization:
      scaler: clamp
      lo: 0.0
      hi: 100.0
      invert: false
```

Extraction methods:

| Method | Description |
|---|---|
| `direct` | Read a field via a dot-notation path from source data |
| `pattern_match` | Check for files matching a pattern group (see `patterns.yaml`) |
| `calculated` | Invoke a named calculation function |
| `existence_check` | Non-null check on a source field |
| `publication` | Aggregate a field across all matched publications (`any`, `mean` or `sum`) |

Normalization scalers:

| Scaler | Description |
|---|---|
| `clamp` | Linearly rescale from $[lo, hi]$ to $[0, 1]$ |
| `log` | Log-scale, capped at `cap` |
| `fraction` | Value is already a fraction in $[0, 1]$ |

Set `invert: true` for metrics where lower raw values should score higher.

## File Patterns (`patterns.yaml`)

Pattern-based metrics (such as `has_workflow_support` and `has_distribution_support`) check the repository file listing against pattern groups:

```yaml
pattern_groups:
  workflow_files:
    - "*.cwl"
    - "main.nf"
    - "nextflow.config"
    - "*.nf"
    - "Snakefile"
    - "*.smk"
    - "*.wdl"
```

Adding a file pattern here (e.g., a new workflow system) automatically extends the corresponding metric. Metrics referencing pattern groups that do not exist are reported as configuration errors.

## Validation

Configuration files are validated when loaded, including cross-references between them:

- Metrics referenced in `weights.yaml` must exist in `metrics.yaml`
- Pattern groups referenced in `metrics.yaml` must exist in `patterns.yaml`

Invalid configuration raises a `ConfigError`.
