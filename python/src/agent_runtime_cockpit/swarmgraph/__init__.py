"""ARC compatibility bridge for the SwarmGraph SDK.

Source ownership moved to the standalone ``swarmgraph-sdk`` distribution
(``packages/swarmgraph-sdk/swarmgraph``). This package re-exports the SDK so
existing ``agent_runtime_cockpit.swarmgraph.*`` imports keep working without
duplicating logic.

Critical: submodule imports such as
``from agent_runtime_cockpit.swarmgraph.config import SwarmGraphConfig`` must
resolve to the *same* module object as ``swarmgraph.config`` so that Pydantic
class identity is preserved across the two import paths. A naive ``__path__``
extension would re-execute the source files under a second module name,
producing distinct (incompatible) classes. To avoid that, this bridge installs
a ``MetaPathFinder`` that aliases ``agent_runtime_cockpit.swarmgraph.<name>``
to the already-imported ``swarmgraph.<name>`` module.
"""

# ruff: noqa: E402, F401, F403

from __future__ import annotations

import importlib
import sys
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from types import ModuleType

import swarmgraph as _sdk

_BRIDGE_PREFIX = __name__ + "."
_SDK_PREFIX = _sdk.__name__ + "."


class _SwarmGraphBridgeFinder(MetaPathFinder, Loader):
    """Aliases ``agent_runtime_cockpit.swarmgraph.X`` to ``swarmgraph.X``."""

    def find_spec(self, fullname, path=None, target=None):  # noqa: ANN001
        if not fullname.startswith(_BRIDGE_PREFIX):
            return None
        return ModuleSpec(fullname, self)

    def create_module(self, spec: ModuleSpec) -> ModuleType:
        sdk_name = _SDK_PREFIX + spec.name[len(_BRIDGE_PREFIX) :]
        module = importlib.import_module(sdk_name)
        sys.modules[spec.name] = module
        return module

    def exec_module(self, module: ModuleType) -> None:  # already initialized
        return None


# Install once; the finder is idempotent for repeated imports.
if not any(isinstance(f, _SwarmGraphBridgeFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _SwarmGraphBridgeFinder())

# Point this package's submodule search at the SDK package so that any code
# walking ``__path__`` (e.g. pkgutil) still finds the real source.
__path__ = list(getattr(_sdk, "__path__", []))

# Re-export the full public API from the SDK package.
from swarmgraph import *  # noqa: F401,F403
from swarmgraph import __all__ as __all__  # noqa: F401
