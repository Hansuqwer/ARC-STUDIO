from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_sibling_adapter(package_file: str, module_name: str) -> ModuleType:
    adapter_path = Path(package_file).resolve().parent.with_suffix(".py")
    spec_name = f"agent_runtime_cockpit.adapters._{module_name}_adapter"
    spec = importlib.util.spec_from_file_location(spec_name, adapter_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {module_name} adapter from {adapter_path}")
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "agent_runtime_cockpit.adapters"
    sys.modules[spec_name] = module
    spec.loader.exec_module(module)
    return module
