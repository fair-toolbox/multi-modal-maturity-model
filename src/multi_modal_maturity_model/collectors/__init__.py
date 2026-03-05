from .biotools import BioToolsCollector
from .lizard import CodeQualityCollector
from .github import GitHubCollector
from .gitlab import GitlabCollector
from .europe_pmc import EuropePMCCollector
from .howfairis import FairnessCollector

__all__ = ["BioToolsCollector", "CodeQualityCollector", "GitHubCollector", "GitlabCollector", "EuropePMCCollector", "FairnessCollector"]
