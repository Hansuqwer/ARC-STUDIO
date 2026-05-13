"""
Helper module for loading adapters in examples.

This module provides a utility function to load adapter classes
from .py files, bypassing the subdirectory modules.
"""
import importlib.util
from pathlib import Path


def load_adapter_class(module_name: str, class_name: str):
    """
    Load adapter class from .py file directly.
    
    Args:
        module_name: Name of the module (e.g., 'swarmgraph')
        class_name: Name of the class (e.g., 'SwarmGraphAdapter')
    
    Returns:
        The adapter class
    """
    adapters_dir = Path(__file__).parent.parent.parent / "src" / "agent_runtime_cockpit" / "adapters"
    
    spec = importlib.util.spec_from_file_location(
        f"agent_runtime_cockpit.adapters.{module_name}",
        adapters_dir / f"{module_name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)


# Pre-load common adapters
SwarmGraphAdapter = load_adapter_class("swarmgraph", "SwarmGraphAdapter")
LangGraphAdapter = load_adapter_class("langgraph", "LangGraphAdapter")
CrewAIAdapter = load_adapter_class("crewai", "CrewAIAdapter")
OpenAIAgentsAdapter = load_adapter_class("openai_agents", "OpenAIAgentsAdapter")
