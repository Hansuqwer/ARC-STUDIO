"""
SwarmGraph adapter package.

The main adapter class is defined in the parent swarmgraph.py module.
This package contains helper modules for SwarmGraph integration.
"""
from .._compat import load_sibling_adapter

# Export the main classes
_module = load_sibling_adapter(__file__, "swarmgraph")
SwarmGraphAdapter = _module.SwarmGraphAdapter
SWARMGRAPH_ENV_ALLOWLIST = _module.SWARMGRAPH_ENV_ALLOWLIST

__all__ = ["SwarmGraphAdapter", "SWARMGRAPH_ENV_ALLOWLIST"]
