# Contributing

Contributions are welcome! This project lives at [github.com/fair-toolbox/multi-modal-maturity-model](https://github.com/fair-toolbox/multi-modal-maturity-model).

## Getting Started

```bash
git clone https://github.com/fair-toolbox/multi-modal-maturity-model.git
cd multi-modal-maturity-model

# Install with dev dependencies (Python 3.12+)
pip install -e . --group dev

# Run the tests
pytest
```

## Workflow

1. Fork the repository and create a branch from `develop`.
2. Make your changes, with tests where applicable.
3. Run `pytest` and make sure everything passes.
4. Open a pull request against `develop`.

Please keep pull requests focused — one feature or fix per PR.

## Code Style

The project uses `pre-commit` for formatting and linting:

```bash
pre-commit install
pre-commit run --all-files
```

## Documentation

The documentation is built with [MkDocs](https://www.mkdocs.org) (Material theme) and lives in `docs/`. To preview it locally:

```bash
pip install -r docs/requirements.txt
mkdocs serve
```

Then open [http://localhost:8000](http://localhost:8000). Documentation changes are deployed automatically on push to `develop`.

## Reporting Issues

Found a bug or have a feature request? Please open an issue at [github.com/fair-toolbox/multi-modal-maturity-model/issues](https://github.com/fair-toolbox/multi-modal-maturity-model/issues).
