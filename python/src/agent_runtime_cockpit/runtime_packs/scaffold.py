"""Safe, minimal runtime pack scaffolding.

``init_pack`` writes a small, valid, secret-free runtime pack skeleton to a local
directory. The generated manifest is fail-closed (no dangerous permissions, no
paid models, no IR export) and is hash-pinned so ``arc runtime-pack validate``
passes immediately. No code is generated or executed and nothing is fetched.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from .hashing import manifest_hash
from .models import (
    MANIFEST_FILENAME,
    RuntimeIdentity,
    RuntimeKind,
    RuntimePackManifest,
    RuntimePackProvenance,
)


class ScaffoldError(Exception):
    """Raised when a pack cannot be scaffolded (for example, target not empty)."""


_EXAMPLE_WORKFLOW = {
    "name": "minimal",
    "description": "A placeholder workflow this runtime can describe to ARC.",
    "nodes": [{"id": "start", "type": "task", "label": "do something"}],
    "edges": [],
}

_README_TEMPLATE = """# {name}

An ARC **runtime pack** for `{runtime}`.

A runtime pack is static, inspectable metadata describing how this runtime
integrates with ARC. It contains **no secrets** and is never executed during
discovery, validation, or installation.

## Commands

```bash
arc runtime-pack validate .
arc runtime-pack inspect .
arc runtime-pack install .
arc runtime-pack doctor .
```

## What to edit

Open `{manifest}` and declare:

* `capabilities` — what the runtime can do (all flags fail closed to `false`).
* `permissions` — what access it needs (network / filesystem / mcp / ...).
  Dangerous permissions must include a `reason`.
* `entrypoints` — `module:function` references (never executed in the MVP).
* `ir` — set `can_export_ir` and `supported_ir_version` if you emit SwarmGraph IR.

After editing, run `arc runtime-pack validate .` to re-pin the manifest hash.
"""

_TESTS_README = """# Tests for this runtime pack

Add example workflows under `examples/` and reference them from the manifest's
`tests.examples` list. ARC validates manifests statically; it does not run pack
code, so tests here should exercise *your* adapter, not ARC.
"""


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def build_scaffold_manifest(
    pack_id: str,
    name: str,
    *,
    runtime_name: str | None = None,
    runtime_kind: RuntimeKind = RuntimeKind.UNKNOWN,
    language: str = "python",
    generated_by: str = "arc runtime-pack init",
    git_commit: str | None = None,
) -> RuntimePackManifest:
    """Build a minimal, valid, fail-closed manifest model (does not write files)."""
    manifest = RuntimePackManifest(
        id=pack_id,
        name=name,
        version="0.1.0",
        description=f"Runtime pack for {runtime_name or pack_id}.",
        runtime=RuntimeIdentity(
            runtime_name=runtime_name or pack_id,
            runtime_kind=runtime_kind,
            language=language,
        ),
        provenance=RuntimePackProvenance(
            created_at=_now_iso(),
            generated_by=generated_by,
            git_commit=git_commit,
        ),
        metadata={"tests": {"examples": ["examples/minimal.workflow.json"]}},
    )
    # tests.examples points at the generated example workflow.
    manifest.tests.examples = ["examples/minimal.workflow.json"]
    manifest.manifest_hash = manifest_hash(manifest)
    return manifest


def init_pack(
    target: Path | str,
    pack_id: str,
    name: str,
    *,
    runtime_name: str | None = None,
    runtime_kind: RuntimeKind = RuntimeKind.UNKNOWN,
    language: str = "python",
    force: bool = False,
) -> list[Path]:
    """Create a minimal runtime pack at ``target``.

    Returns the list of created file paths. Raises :class:`ScaffoldError` if the
    target already contains a manifest and ``force`` is not set.
    """
    target_dir = Path(target)
    manifest_path = target_dir / MANIFEST_FILENAME
    if manifest_path.exists() and not force:
        raise ScaffoldError(
            f"{MANIFEST_FILENAME} already exists at {target_dir}; pass force=True to overwrite."
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "examples").mkdir(parents=True, exist_ok=True)
    (target_dir / "tests").mkdir(parents=True, exist_ok=True)

    manifest = build_scaffold_manifest(
        pack_id,
        name,
        runtime_name=runtime_name,
        runtime_kind=runtime_kind,
        language=language,
    )

    created: list[Path] = []

    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    created.append(manifest_path)

    readme_path = target_dir / "README.md"
    readme_path.write_text(
        _README_TEMPLATE.format(
            name=name,
            runtime=runtime_name or pack_id,
            manifest=MANIFEST_FILENAME,
        ),
        encoding="utf-8",
    )
    created.append(readme_path)

    example_path = target_dir / "examples" / "minimal.workflow.json"
    example_path.write_text(
        json.dumps(_EXAMPLE_WORKFLOW, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    created.append(example_path)

    tests_readme_path = target_dir / "tests" / "README.md"
    tests_readme_path.write_text(_TESTS_README, encoding="utf-8")
    created.append(tests_readme_path)

    return created


__all__ = [
    "ScaffoldError",
    "build_scaffold_manifest",
    "init_pack",
]
