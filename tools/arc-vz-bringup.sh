#!/usr/bin/env bash
#
# arc-vz-bringup.sh — reproducible macOS Apple-VZ microVM bring-up for ARC.
#
# Mirrors the proven, fully open-source path:
#   static Alpine BusyBox  ->  Kata `vmlinux.container` kernel (uncompressed
#   arm64 Image with virtiofs built in)  ->  packed exec initrd  ->  compiled +
#   ad-hoc-signed Swift VZ runner + artifact manifest  ->  (optional, gated)
#   `arc sandbox run --provider microvm -- pwd` proof.
#
# By default this only *produces artifacts* (no VM boots). Pass --run-proof to
# run the gated proof, which sets ARC_MICROVM_EXEC_ENABLED / ARC_MICROVM_INTEGRATION
# / ARC_VZ_REAL_EXEC for a single guest-available-command demonstration. That is
# a gated, default-off proof — NOT a production-grade or arbitrary-command
# microVM. See docs/adr/ADR-024-microvm-public-execution-contract.md.
#
# Requires: macOS arm64, uv, swiftc + codesign (Xcode CLT), and — only when the
# BusyBox cache is empty — a running Docker engine (for the busybox-static build).
#
# USAGE:
#   tools/arc-vz-bringup.sh [--run-proof] [--force] [--cache DIR]
#                           [--kata-version VER] [--workspace DIR]
#
set -euo pipefail

KATA_VERSION="${ARC_KATA_VERSION:-3.31.0}"
ARCH="${ARC_VZ_ARCH:-arm64}"
CACHE="${ARC_VZ_CACHE:-$HOME/.cache/arc/microvm}"
WORKSPACE="${ARC_VZ_WORKSPACE:-}"
RUN_PROOF=0
FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --run-proof) RUN_PROOF=1; shift ;;
    --force) FORCE=1; shift ;;
    --cache) CACHE="${2:?--cache needs a dir}"; shift 2 ;;
    --kata-version) KATA_VERSION="${2:?--kata-version needs a value}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?--workspace needs a dir}"; shift 2 ;;
    -h | --help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PY="$ROOT/python"

log() { printf '>> %s\n' "$*"; }
die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

[ "$(uname -s)" = "Darwin" ] || die "macOS required (Apple Virtualization.framework)"
case "$ARCH" in
  arm64 | aarch64) ;;
  *) die "only arm64 is supported (got '$ARCH')" ;;
esac
command -v uv >/dev/null 2>&1 || die "uv not found (needed to run arc)"
[ -d "$PY" ] || die "python project not found at $PY"

mkdir -p "$CACHE"
BUSYBOX="$CACHE/busybox"
KERNEL="$CACHE/vmlinux.container"
INITRD_DIR="$CACHE/initrd"
ART="$CACHE/artifacts"

# --- 1. static BusyBox -------------------------------------------------------
if [ "$FORCE" = 1 ] || [ ! -x "$BUSYBOX" ]; then
  log "building static BusyBox -> $BUSYBOX"
  "$SCRIPT_DIR/build-arc-vz-busybox.sh" --output "$BUSYBOX" --arch "$ARCH"
else
  log "BusyBox cached: $BUSYBOX"
fi

# --- 2. Kata vmlinux.container kernel ----------------------------------------
STAMP="$CACHE/.kata-version"
if [ "$FORCE" = 1 ] || [ ! -f "$KERNEL" ] || [ "$(cat "$STAMP" 2>/dev/null || true)" != "$KATA_VERSION" ]; then
  url="https://github.com/kata-containers/kata-containers/releases/download/${KATA_VERSION}/kata-static-${KATA_VERSION}-${ARCH}.tar.zst"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  log "downloading Kata $KATA_VERSION kernel bundle (~660MB, cached after first run)"
  curl -L --fail -sS -o "$tmp/kata.tar.zst" "$url" || die "kata download failed: $url"
  base="./opt/kata/share/kata-containers"
  log "extracting $base/vmlinux.container"
  tar -xf "$tmp/kata.tar.zst" -C "$tmp" "$base/vmlinux.container" || die "vmlinux.container not in bundle"
  tgt="$(readlink "$tmp/$base/vmlinux.container" || true)"
  [ -n "$tgt" ] || die "could not resolve vmlinux.container symlink target"
  tar -xf "$tmp/kata.tar.zst" -C "$tmp" "$base/$tgt" || die "kernel file '$tgt' not in bundle"
  cp "$tmp/$base/$tgt" "$KERNEL"
  rm -rf "$tmp"
  trap - EXIT
  echo "$KATA_VERSION" >"$STAMP"
else
  log "kernel cached: $KERNEL (kata $KATA_VERSION)"
fi
# A VZ-bootable arm64 kernel is a raw Image: byte0 'MZ', magic@0x38 'ARM\x64'.
magic="$(xxd -s 0x38 -l 4 -p "$KERNEL" 2>/dev/null || true)"
[ "$magic" = "41524d64" ] ||
  die "kernel is not a raw arm64 Image (magic@0x38='$magic', expected 41524d64); a compressed vmlinuz will not boot under VZ"
log "kernel verified: raw arm64 Image (magic@0x38=ARM\\x64)"

# --- 3. pack exec initrd -----------------------------------------------------
log "packing exec initrd"
(cd "$PY" && uv run arc sandbox vz-artifacts --json --exec-init --pack-initrd \
  --busybox "$BUSYBOX" --output "$INITRD_DIR") >"$CACHE/.initrd.json"
python3 - "$CACHE/.initrd.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])).get("data", {})
blockers = d.get("blockers") or []
if not d.get("packed_initrd") or blockers:
    print("initrd pack failed:", blockers, file=sys.stderr)
    sys.exit(1)
PY
INITRD="$INITRD_DIR/arc-vz-exec-initrd.gz"
[ -f "$INITRD" ] || die "initrd not produced at $INITRD"
log "initrd: $INITRD"

# --- 4. runner + artifact manifest -------------------------------------------
log "building Swift VZ runner + manifest (ad-hoc signed)"
(cd "$PY" && uv run arc sandbox vz-artifacts --json --output "$ART" \
  --kernel "$KERNEL" --initrd "$INITRD" --build-runner) >"$CACHE/.art.json"
python3 - "$CACHE/.art.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])).get("data", {})
blockers = d.get("blockers") or []
if blockers or not d.get("runner_built") or not d.get("runner_signed"):
    print("runner/manifest build failed:", blockers, file=sys.stderr)
    sys.exit(1)
PY
MANIFEST="$ART/vz-artifacts-manifest.json"
[ -f "$MANIFEST" ] || die "manifest not produced at $MANIFEST"
log "manifest: $MANIFEST"

# --- 5. optional gated proof -------------------------------------------------
if [ "$RUN_PROOF" = 1 ]; then
  ws="${WORKSPACE:-$CACHE/ws}"
  mkdir -p "$ws"
  log "running GATED proof (default-off path): arc sandbox run --provider microvm -- pwd"
  set +e
  (cd "$ws" && ARC_MICROVM_EXEC_ENABLED=1 ARC_MICROVM_INTEGRATION=1 ARC_VZ_REAL_EXEC=1 \
    ARC_VZ_ARTIFACT_MANIFEST="$MANIFEST" \
    uv run --project "$PY" arc sandbox run --provider microvm --json --workspace "$ws" -- pwd) \
    >"$CACHE/.proof.json" 2>&1
  set -e
  python3 - "$CACHE/.proof.json" <<'PY'
import json, sys
raw = open(sys.argv[1]).read()
try:
    d = json.loads(raw)
except Exception:
    print("proof produced non-JSON output:\n" + raw[-600:], file=sys.stderr)
    sys.exit(1)


def find(o, k):
    if isinstance(o, dict):
        if k in o and o[k] is not None:
            return o[k]
        for v in o.values():
            r = find(v, k)
            if r is not None:
                return r
    return None


ok = d.get("ok")
errs = find(d, "lifecycle_errors")
lifecycle = find(d, "lifecycle")
print("   ok:", ok)
print("   lifecycle:", lifecycle)
print("   errors:", errs)
if not ok or errs:
    print("GATED PROOF FAILED", file=sys.stderr)
    sys.exit(1)
print("   GATED PROOF PASSED — single guest-available-command demonstration (default-off; not production-grade)")
PY
else
  log "artifacts ready (no VM booted). To run the gated proof:"
  echo "     cd $PY && \\"
  echo "       ARC_MICROVM_EXEC_ENABLED=1 ARC_MICROVM_INTEGRATION=1 ARC_VZ_REAL_EXEC=1 \\"
  echo "       ARC_VZ_ARTIFACT_MANIFEST=\"$MANIFEST\" \\"
  echo "       uv run arc sandbox run --provider microvm -- pwd"
  echo "   ...or re-run with: $0 --run-proof"
fi
log "done."
