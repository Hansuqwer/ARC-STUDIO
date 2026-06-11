#!/usr/bin/env bash
# CI gate for arc-v2 improvement #1: the arc-ui facade is the ONLY crate that
# may depend on a UI framework. Hardened per review report §6.5:
#  (a) catches `use gpui...` / `use floem...` imports,
#  (b) catches fully-qualified `gpui::` / `floem::` paths,
#  (c) catches Cargo.toml dependency declarations outside arc-ui/spikes.
set -euo pipefail
cd "$(dirname "$0")/.."

fail=0

src_violations=$(grep -rn --include='*.rs' -E '(^[[:space:]]*use[[:space:]]+(gpui|floem))|((^|[^[:alnum:]_])(gpui|floem)::)' rust/ 2>/dev/null \
  | grep -v '^rust/arc-ui/' | grep -v '^rust/spikes/' | grep -v '^rust/target/' || true)
if [ -n "$src_violations" ]; then
  echo "Framework types leaked outside arc-ui:"; echo "$src_violations"; fail=1
fi

dep_violations=$(grep -rn --include='Cargo.toml' -E '^[[:space:]]*(gpui|floem)[[:space:]]*=' rust/ 2>/dev/null \
  | grep -v '^rust/arc-ui/' | grep -v '^rust/spikes/' || true)
if [ -n "$dep_violations" ]; then
  echo "Framework dependency declared outside arc-ui:"; echo "$dep_violations"; fail=1
fi

if [ "$fail" -ne 0 ]; then exit 1; fi
echo "OK: arc-ui facade holds."
