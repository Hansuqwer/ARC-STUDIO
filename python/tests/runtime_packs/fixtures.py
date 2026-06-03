"""Build and write the canonical JSON fixture files for cross-language parity tests.

Running this module directly (``python -m tests.runtime_packs.fixtures``) writes
``valid_minimal.json`` and ``valid_ir.json`` into:

  * ``python/tests/runtime_packs/fixtures/``
  * ``packages/arc-protocol-ts/src/fixtures/runtime-pack/``

The files contain real, computed manifest_hashes so the TypeScript tests can
assert that the Python-generated JSON validates against the TS type interfaces.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", message=r"Field name .* shadows an attribute in parent")

from conftest import make_ir_manifest, make_minimal_manifest  # type: ignore  # noqa: E402


def _write(dest: Path, manifest) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = manifest.model_dump(mode="json")
    dest.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  wrote {dest}  (hash={payload.get('manifest_hash', '')[:16]}...)")


def build_fixtures(
    py_fixture_dir: Path,
    ts_fixture_dir: Path,
) -> None:
    print("Building canonical Runtime Pack fixture files …")
    for name, manifest in [
        ("valid_minimal.json", make_minimal_manifest()),
        ("valid_ir.json", make_ir_manifest()),
    ]:
        _write(py_fixture_dir / name, manifest)
        _write(ts_fixture_dir / name, manifest)
    print("Done.")


if __name__ == "__main__":
    repo = Path(__file__).parent.parent.parent.parent  # arc/python → arc
    build_fixtures(
        py_fixture_dir=Path(__file__).parent / "fixtures",
        ts_fixture_dir=repo / "packages" / "arc-protocol-ts" / "src" / "fixtures" / "runtime-pack",
    )
