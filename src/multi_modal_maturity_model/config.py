"""Configuration management for Multi-Modal Maturity Model."""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class MetricsConfig(BaseModel):
    """Configuration for metrics extraction.

    Attributes
    ----------
    metrics : dict[str, dict[str, Any]]
        Metric definitions loaded from metrics.yaml
    extraction_methods : dict[str, dict[str, Any]]
        Extraction method documentation
    normalization_methods : dict[str, dict[str, Any]]
        Normalization method documentation
    """

    metrics: dict[str, dict[str, Any]] = Field(default_factory=dict)
    extraction_methods: dict[str, dict[str, Any]] = Field(default_factory=dict)
    normalization_methods: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> "MetricsConfig":
        """Load metrics configuration from YAML file.

        Parameters
        ----------
        path : Path
            Path to metrics.yaml file

        Returns
        -------
        MetricsConfig
            Loaded configuration
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(
            metrics=data.get("metrics", {}),
            extraction_methods=data.get("extraction_methods", {}),
            normalization_methods=data.get("normalization_methods", {}),
        )


class PatternsConfig(BaseModel):
    """Configuration for pattern recognition.

    Attributes
    ----------
    workflow_files : dict[str, list[str]]
        File patterns for workflow systems
    distribution_files : dict[str, list[str]]
        File patterns for distribution/packaging
    security_policy_files : list[str]
        File patterns for security policies
    security_scanning_files : dict[str, list[str]]
        File patterns for security scanning configs
    """

    workflow_files: dict[str, list[str]] = Field(default_factory=dict)
    distribution_files: dict[str, list[str]] = Field(default_factory=dict)
    security_policy_files: list[str] = Field(default_factory=list)
    security_scanning_files: dict[str, list[str]] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> "PatternsConfig":
        """Load patterns configuration from YAML file.

        Parameters
        ----------
        path : Path
            Path to patterns.yaml file

        Returns
        -------
        PatternsConfig
            Loaded configuration
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(**data)


class WeightsConfig(BaseModel):
    """Configuration for dimension and overall score weights.

    Attributes
    ----------
    dimensions : dict[str, dict[str, float]]
        Weights for metrics within each dimension
    overall : dict[str, float]
        Weights for dimensions in overall score
    """

    dimensions: dict[str, dict[str, float]] = Field(default_factory=dict)
    overall: dict[str, float] = Field(default_factory=dict)

    @field_validator("dimensions", "overall")
    @classmethod
    def validate_weights(cls, v: dict) -> dict:
        """Validate that all weights are non-negative.

        Parameters
        ----------
        v : dict
            Dictionary of weights

        Returns
        -------
        dict
            Validated weights

        Raises
        ------
        ValueError
            If any weight is negative
        """
        for key, value in v.items():
            if isinstance(value, dict):
                for metric, weight in value.items():
                    if weight < 0:
                        raise ValueError(
                            f"Weight for {key}.{metric} must be non-negative, got {weight}"
                        )
            elif value < 0:
                raise ValueError(f"Weight for {key} must be non-negative, got {value}")
        return v

    @classmethod
    def from_yaml(cls, path: Path) -> "WeightsConfig":
        """Load weights configuration from YAML file.

        Parameters
        ----------
        path : Path
            Path to weights.yaml file

        Returns
        -------
        WeightsConfig
            Loaded configuration
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def apply_overrides(self, overrides: dict[str, Any]) -> "WeightsConfig":
        """Apply runtime weight overrides.

        Parameters
        ----------
        overrides : dict[str, Any]
            Dictionary with 'dimensions' and/or 'overall' keys

        Returns
        -------
        WeightsConfig
            New config with overrides applied
        """
        dimensions = self.dimensions.copy()
        overall = self.overall.copy()

        if "dimensions" in overrides:
            for dim, weights in overrides["dimensions"].items():
                if dim in dimensions:
                    dimensions[dim].update(weights)
                else:
                    dimensions[dim] = weights

        if "overall" in overrides:
            overall.update(overrides["overall"])

        return WeightsConfig(dimensions=dimensions, overall=overall)


class APIConfig(BaseSettings):
    """API credentials and tokens from environment variables.

    Attributes
    ----------
    github_token : str | None
        GitHub personal access token
    gitlab_token : str | None
        GitLab personal access token
    altmetric_api_key : str | None
        Altmetric API key
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    github_token: Optional[str] = Field(None, alias="GITHUB_TOKEN")
    gitlab_token: Optional[str] = Field(None, alias="GITLAB_TOKEN")
    altmetric_api_key: Optional[str] = Field(None, alias="ALTMETRIC_API_KEY")


class AppConfig(BaseModel):
    """Main application configuration.

    Attributes
    ----------
    metrics : MetricsConfig
        Metrics extraction configuration
    patterns : PatternsConfig
        Pattern recognition configuration
    weights : WeightsConfig
        Dimension and overall score weights
    api : APIConfig
        API credentials and tokens
    """

    metrics: MetricsConfig
    patterns: PatternsConfig
    weights: WeightsConfig
    api: APIConfig

    @classmethod
    def load(
        cls,
        config_path: Optional[Path] = None,
    ) -> "AppConfig":
        """Load configuration from multiple sources with precedence.

        Configuration is loaded in the following order (later overrides earlier):
        1. Package defaults (config/*.yaml)
        2. Explicit config path (config_path parameter)

        Parameters
        ----------
        config_path : Path | None, optional
            Explicit path to configuration file

        Returns
        -------
        AppConfig
            Loaded and merged configuration
        """
        # Load package defaults
        default_dir = Path(__file__).parent.parent.parent / "config"

        metrics = MetricsConfig.from_yaml(default_dir / "metrics.yaml")
        patterns = PatternsConfig.from_yaml(default_dir / "patterns.yaml")
        weights = WeightsConfig.from_yaml(default_dir / "weights.yaml")
        api = APIConfig()

        if config_path and config_path.exists():
            logger.info(f"Loading configuration from {config_path}")
            weights = cls._merge_weights_from_file(weights, config_path)

        return cls(metrics=metrics, patterns=patterns, weights=weights, api=api)

    @staticmethod
    def _merge_weights_from_file(
        base_weights: WeightsConfig, config_file: Path
    ) -> WeightsConfig:
        """Merge weights from a config file into base weights.

        Parameters
        ----------
        base_weights : WeightsConfig
            Base weights configuration
        config_file : Path
            Path to YAML config file

        Returns
        -------
        WeightsConfig
            Merged weights configuration
        """
        with open(config_file) as f:
            data = yaml.safe_load(f)

        if not data:
            return base_weights

        overrides = {}
        if "dimensions" in data:
            overrides["dimensions"] = data["dimensions"]
        if "overall" in data:
            overrides["overall"] = data["overall"]

        if overrides:
            return base_weights.apply_overrides(overrides)

        return base_weights

    def get_dimension_weights(self, dimension: str) -> dict[str, float]:
        return self.weights.dimensions[dimension]

    def get_overall_weights(self) -> dict[str, float]:
        return self.weights.overall
