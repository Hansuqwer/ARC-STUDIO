"""
SwarmGraph adapter package.

The main adapter class is defined in the parent swarmgraph.py module.
This package contains helper modules for SwarmGraph integration.
"""
# Import from parent module to make SwarmGraphAdapter available
import sys
from pathlib import Path

# Load the swarmgraph.py module from parent directory
import importlib.util
_parent_module_path = Path(__file__).parent.parent / "swarmgraph.py"
_spec = importlib.util.spec_from_file_location("_swarmgraph_adapter", _parent_module_path)
_module = importlib.util.module_from_spec(_spec)

# Set up the module in sys.modules with proper parent package
_module.__package__ = "agent_runtime_cockpit.adapters"
sys.modules["agent_runtime_cockpit.adapters._swarmgraph_adapter"] = _module
_spec.loader.exec_module(_module)

# Export the main classes
SwarmGraphAdapter = _module.SwarmGraphAdapter
SWARMGRAPH_ENV_ALLOWLIST = _module.SWARMGRAPH_ENV_ALLOWLIST

__all__ = ["SwarmGraphAdapter", "SWARMGRAPH_ENV_ALLOWLIST"]
