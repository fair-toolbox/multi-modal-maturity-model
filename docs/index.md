# Multi-Modal Maturity Model (MMMM)

## Overview

The Multi-Modal Maturity Model is being developed for Work Package 1 of the [TDCC-LSH](https://tdcc.nl) project ["A FAIR tool framework for bioinformatics services, tools and workflows in digital Life Sciences and Health (LSH) research"](https://tdcc.nl/projects/tdcc-lsh-project-initiatives/).

The purpose of MMMM is to provide a **quantitative measure of maturity** for research software and related services, aggregated along a number of modalities, dimensions or categories, balancing sensitivity to incremental improvements and general robustness.

## Multi-Modal

MMMM is truly multi-modal in that it combines several orthogonal approaches:

- **Bibliometrics**: Quantitative metrics like citation counts to measure scientific impact
- **Static Code Analysis**: Code quality, maintainability and security
- **Software Metadata**: FAIRness, sustainability, and compatibility
- **Manual evaluation**: User communities, project governance and scientific uniqueness

## Data Sources

M4 automatically collects data from:

| Source | Used for |
|---|---|
| [GitHub](https://github.com) / [GitLab](https://gitlab.com) | Repository metrics (popularity, issues, contributors, security settings) |
| [bio.tools](https://bio.tools) | Tool registry metadata and supported input/output formats |
| [HowFAIRis](https://github.com/fair-software/howfairis) | FAIRness compliance |
| [OpenAlex](https://openalex.org) | Publication citations, open access status and field-weighted citation impact |
| [Altmetric](https://www.altmetric.com) | Online attention surrounding publications |
| [Lizard](https://github.com/terryyin/lizard) | Static code analysis (size, complexity, duplication) |

## Quick Start

Install (Python 3.12+):

```bash
pip install git+https://github.com/fair-toolbox/multi-modal-maturity-model.git
```

Analyze a repository:

```bash
maturity-model analyze https://github.com/user/repo
```

See the [User Guide](user_guide.md) for more examples and options.

## Project Information

- **Version**: 0.1.0
- **License**: MIT
- **Authors**: Ana Mendes, Magnus Palmblad
- **Repository**: [github.com/fair-toolbox/multi-modal-maturity-model](https://github.com/fair-toolbox/multi-modal-maturity-model)

## Next Steps

- [User Guide](user_guide.md)
- [Dimensions and Metrics](maturity_model.md)
- [Configuration](configuration.md)
- [Contributing](contributing.md)
