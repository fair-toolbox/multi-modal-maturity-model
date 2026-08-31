# Multi-Modal Maturity Model

This Multi-Modal Maturity Model (M4) for research software and services is being developed for Work Package 1 of the [TDCC-LSH](https://tdcc.nl) project ["A FAIR tool framework for bioinformatics services, tools and workflows in digital Life Sciences and Health (LSH) research"](https://tdcc.nl/projects/tdcc-lsh-project-initiatives/). The purpose of the model defined and computed by M4 is to provide a quantitative measure of maturity for research software and related services, aggregated along a number of modalities, dimensions or categories, balancing sensitivity to increamental improvements and general robustness.

The maturity model is truly multi-modal in that it combines several orthogonal approaches such as bibliometrics (focusing on quantitative metrics like citation counts to measure scientific impact), static code analysis (focusing on code quality, maintainability and security), software metadata (to evaluate FAIRness and sustainability), and supports manual evaluation (of user communities, project governance and scientific uniqueness).


# Run

CLI:

```bash
# Use custom config file
maturity-model analyze https://github.com/user/repo \
  --weights my-weights.yaml \
  --output results.json

# Use default weights
maturity-model analyze https://github.com/user/repo -o results.json
```

Python:

```python
from multi_modal_maturity_model import MaturityPipeline

# Auto-load default config
pipeline = MaturityPipeline()

# Load custom weights
pipeline = MaturityPipeline(weights_path="your_weights_path.yaml")
```
