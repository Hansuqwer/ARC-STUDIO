from .._compat import load_sibling_adapter

CrewAIAdapter = load_sibling_adapter(__file__, "crewai").CrewAIAdapter

__all__ = ["CrewAIAdapter"]
