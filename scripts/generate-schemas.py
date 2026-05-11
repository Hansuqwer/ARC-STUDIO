#!/usr/bin/env python3
"""
ARC Schema Generator

Generates JSON Schema files from Pydantic models.
Run: uv run python scripts/generate-schemas.py

Output: docs/schemas/*.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from agent_runtime_cockpit.protocol.schemas import (
    WorkspaceInfo, RuntimeInfo, WorkflowInfo, SchemaInfo,
    RunRecord, RunEvent, ContextPackEntry,
)
from agent_runtime_cockpit.protocol.envelope import ArcEnvelope

MODELS = {
    "WorkspaceInfo": WorkspaceInfo,
    "RuntimeInfo": RuntimeInfo,
    "WorkflowInfo": WorkflowInfo,
    "SchemaInfo": SchemaInfo,
    "RunRecord": RunRecord,
    "RunEvent": RunEvent,
    "ContextPackEntry": ContextPackEntry,
}

output_dir = Path(__file__).parent.parent / "docs" / "schemas"
output_dir.mkdir(parents=True, exist_ok=True)

print("Generating ARC JSON Schemas...")

for name, model in MODELS.items():
    schema = model.model_json_schema()
    out_path = output_dir / f"{name}.json"
    out_path.write_text(json.dumps(schema, indent=2))
    print(f"  ✓ {name} → {out_path}")

# Combined schema index
index = {
    "version": "1.0",
    "models": list(MODELS.keys()),
    "generated": __import__("datetime").datetime.utcnow().isoformat() + "Z",
}
(output_dir / "index.json").write_text(json.dumps(index, indent=2))
print(f"  ✓ index → {output_dir / 'index.json'}")
print(f"\nDone. {len(MODELS)} schemas generated in {output_dir}")
