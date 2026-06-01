"""Local config loader replacing GCP client.

Reads model config from local YAML file instead of GCS.
"""

from pathlib import Path
from typing import Any

import yaml


CONFIG_PATH = Path("config/app_config.yaml")


def load_config() -> dict[str, Any]:
    """Load app config from YAML file.

    Returns:
        Config dict with 'models', 'firebase_collections', 'version_backend'
    """
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

    return config


def get_models() -> list[str]:
    """Get list of all model IDs from config."""
    config = load_config()
    return list(config.get("models", {}).keys())


def get_model_config(model_id: str) -> dict[str, Any]:
    """Get config for a specific model.

    Args:
        model_id: Model identifier (e.g., 'gpt-4o-mini-2024-07-18')

    Returns:
        Model config dict with 'weight', 'tags', 'input_cost', 'output_cost'
    """
    config = load_config()
    models = config.get("models", {})

    if model_id not in models:
        raise ValueError(f"Model not found in config: {model_id}")

    return models[model_id]


def get_models_by_tags(tags: list[str]) -> list[str]:
    """Get models matching any of the specified tags.

    Args:
        tags: List of tags to filter by (e.g., ['fast', 'code'])

    Returns:
        List of model IDs matching at least one tag
    """
    config = load_config()
    models = config.get("models", {})

    matching = []
    for model_id, model_config in models.items():
        model_tags = model_config.get("tags", [])
        if any(tag in model_tags for tag in tags):
            matching.append(model_id)

    return matching


def get_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for a model call.

    Args:
        model_id: Model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD
    """
    model_config = get_model_config(model_id)
    input_cost = model_config.get("input_cost", 0.0)
    output_cost = model_config.get("output_cost", 0.0)

    # Costs are per 1M tokens
    total_cost = (input_tokens * input_cost + output_tokens * output_cost) / 1_000_000
    return total_cost


def get_version() -> str:
    """Get backend version string."""
    config = load_config()
    return config.get("version_backend", "0.0.0")
