# Multi-Modal Maturity Model

This Multi-Modal Maturity Model (M4) for research software and services is being developed for Work Package 1 of the [TDCC-LSH](https://tdcc.nl) project ["A FAIR tool framework for bioinformatics services, tools and workflows in digital Life Sciences and Health (LSH) research"](https://tdcc.nl/projects/tdcc-lsh-project-initiatives/). The purpose of the model defined and computed by M4 is to provide a quantitative measure of maturity for research software and related services, aggregated along a number of modalities, dimensions or categories, balancing sensitivity to increamental improvements and general robustness.

The maturity model is truly multi-modal in that it combines several orthogonal approaches such as bibliometrics (focusing on quantitative metrics like citation counts to measure scientific impact), static code analysis (focusing on code quality, maintainability and security), software metadata (to evaluate FAIRness and sustainability), and supports manual evaluation (of user communities, project governance and scientific uniqueness).


## Quick start

### Requirements

- Python >= 3.11
- Poetry >= 2.0

### Clone

```bash
git clone https://github.com/fair-toolbox/multi-modal-maturity-model.git
cd multi-modal-maturity-model
```

### Install

With poetry:

```bash
poetry install

# enable quality hooks
poetry run pre-commit install
```

With pip:

```bash
pip install .
```

### Using the tool

Use the CLI:

```bash
poetry run m4 evaluate --help
```

## Documentation

The documentation is available at [https://fair-toolbox.github.io/multi-modal-maturity-model/](https://fair-toolbox.github.io/multi-modal-maturity-model/)



---
## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
