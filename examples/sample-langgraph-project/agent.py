"""
Sample LangGraph ReAct agent — detected by ARC's LangGraph adapter.
"""
from state import AgentState

try:
    from langgraph.graph import StateGraph, END

    # Build the graph (detected by ARC AST scanner)
    builder = StateGraph(AgentState)
    builder.add_node("agent", lambda state: state)
    builder.add_node("tools", lambda state: state)
    builder.add_edge("agent", "tools")
    builder.add_conditional_edges("agent", lambda s: "tools" if s.get("next") == "tools" else END)
    graph = builder.compile()

except ImportError:
    # LangGraph not installed — ARC will use AST scan + fixture
    graph = None
