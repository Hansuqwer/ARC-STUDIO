from .._compat import load_sibling_adapter

LangGraphAdapter = load_sibling_adapter(__file__, "langgraph").LangGraphAdapter

__all__ = ["LangGraphAdapter"]
