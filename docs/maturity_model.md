# Maturity Model

## Sources

MMMM automatically collects data from the following sources when analyzing a repository:

| Source | Used for |
|---|---|
| GitHub / GitLab API | Repository metrics: popularity, issues, contributors, security settings, file listing |
| [bio.tools](https://bio.tools) | Registry presence and supported input/output data formats |
| [HowFAIRis](https://github.com/fair-software/howfairis) | FAIRness compliance checks |
| [OpenAlex](https://openalex.org) | Publication citations, open access status, field-weighted citation impact (FWCI) |
| [Altmetric](https://www.altmetric.com) | Altmetric Attention Score of publications |
| [Lizard](https://github.com/terryyin/lizard) | Static code analysis: size, complexity, duplication |

Publication metrics require one or more DOIs to be passed via `--doi` (CLI) or `dois` (Python). Registry and format metrics benefit from a bio.tools identifier passed via `--biotools` / `biotools_id`.

## Dimensions

The overall maturity score is a weighted combination of six dimensions. Default overall weights are shown between parentheses.

### Compatibility (0.20)

How well the tool interoperates with common workflow systems and distribution channels.

| Metric | Weight | Description | Source |
|---|---|---|---|
| `input_formats` | 0.25 | Fraction of supported input data formats (EDAM leaf nodes) | bio.tools |
| `output_formats` | 0.25 | Fraction of supported output data formats (EDAM leaf nodes) | bio.tools |
| `has_workflow_support` | 0.25 | Presence of workflow system files (CWL, Nextflow, Snakemake, WDL) | GitHub/GitLab |
| `has_distribution_support` | 0.25 | Presence of packaging/distribution files (Docker, Conda, Python package) | GitHub/GitLab |

### FAIRness (0.20)

Compliance with the FAIR principles for research software, following the [HowFAIRis](https://fair-software.eu) recommendations.

| Metric | Weight | Description | Source |
|---|---|---|---|
| `license` | 0.20 | Presence of a software license | HowFAIRis |
| `repository` | 0.30 | Code available in a public repository | HowFAIRis |
| `registry` | 0.20 | Tool is registered in a registry (e.g., bio.tools) | HowFAIRis |
| `citation` | 0.10 | Presence of citation information | HowFAIRis |
| `checklist` | 0.10 | Presence of a development checklist | HowFAIRis |
| `publication_open_access` | 0.10 | Publication is available as open access | OpenAlex |

### Maintainability (0.20)

Code quality from static analysis.

| Metric | Weight | Description | Source |
|---|---|---|---|
| `nloc_per_file` | 0.30 | Average number of lines of code per file (lower is better) | Lizard |
| `avg_ccn` | 0.40 | Average cyclomatic complexity per function (lower is better) | Lizard |
| `duplicate_rate` | 0.30 | Code duplication percentage (lower is better) | Lizard |

### Sustainability (0.20)

Health of the project and its developer community.

| Metric | Weight | Description | Source |
|---|---|---|---|
| `avg_issue_close_time_days` | 0.40 | Average time to close issues in days (lower is better) | GitHub/GitLab |
| `num_open_issues` | 0.30 | Number of currently open issues (lower is better) | GitHub/GitLab |
| `days_since_last_commit` | 0.20 | Days since the last commit (lower is better) | GitHub/GitLab |
| `inverse_simpson_index` | 0.10 | Contributor diversity (higher is more diverse) | GitHub/GitLab |

### Security (0.10)

Protection of the codebase and its development infrastructure.

| Metric | Weight | Description | Source |
|---|---|---|---|
| `default_branch_protected` | 0.34 | Default branch has protection rules enabled | GitHub/GitLab |
| `has_security_policy` | 0.33 | Presence of a documented security policy (`SECURITY.md`) | GitHub/GitLab |
| `gitignore_present` | 0.01 | Presence of a `.gitignore` file | GitHub/GitLab |
| `security_updates` | 0.01 | Automated security updates enabled (e.g., Dependabot) | GitHub |
| `secret_scanning` | 0.01 | Secret scanning enabled in the repository | GitHub |

### Scientific Impact (0.10)

Academic influence and community attention.

| Metric | Weight | Description | Source |
|---|---|---|---|
| `fwci` | 0.30 | Field-Weighted Citation Impact score | OpenAlex |
| `citation_count` | 0.10 | Total number of citations received | OpenAlex |
| `star_count` | 0.20 | Number of repository stars | GitHub/GitLab |
| `fork_count` | 0.10 | Number of repository forks | GitHub/GitLab |
| `altmetric_score` | 0.10 | Altmetric Attention Score | Altmetric |

## Scoring

Each metric is normalized to the range $[0, 1]$ (see [How Scoring Works](user_guide.md#how-scoring-works)). Dimension scores are weighted averages of their metrics, and the overall score is a weighted average of the dimension scores. Metrics that cannot be computed for a given repository are excluded, and the remaining weights are renormalized.

All weights can be customized — see [Configuration](configuration.md).
