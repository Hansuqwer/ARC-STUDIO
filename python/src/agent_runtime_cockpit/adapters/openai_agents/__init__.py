from .._compat import load_sibling_adapter

OpenAIAgentsAdapter = load_sibling_adapter(__file__, "openai_agents").OpenAIAgentsAdapter

__all__ = ["OpenAIAgentsAdapter"]
