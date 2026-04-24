"""Multi-Modal Maturity Model for research software."""

from .service import MaturityService
from .scoring import DimensionScorer
from .mapper import MaturityMapper

__version__ = "0.1.0"

__all__ = [
    "MaturityService",
    "MaturityMapper",
    "DimensionScorer",
]
