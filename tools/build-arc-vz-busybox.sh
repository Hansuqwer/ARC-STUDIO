#!/usr/bin/env bash
#
# build-arc-vz-busybox.sh — produce a static Linux BusyBox for the ARC VZ
# microVM guest initramfs (unblocks `arc sandbox vz-artifacts --pack-initrd`).
#
# WHY: the VZ initrd packer rejects a dynamically linked BusyBox
# (`ARC_VZ_BUSYBOX must be a static Linux BusyBox binary`, see
# isolation/vz_provider.py::_looks_static_linux_binary). A static binary has no
# embedded dynamic-loader path (/lib/ld-musl, /lib/ld-linux, ...), so it can run
# in a minimal initramfs that ships no shared libraries.
#
# HOW: this uses Docker to install Alpine's apk-signature-verified
# `busybox-static` package for the requested Linux architecture and copies the
# statically linked binary out. No source download / manual checksum pinning is
# needed because apk verifies package signatures inside the container.
#
# TRUTH / SCOPE: this script only *produces the guest BusyBox binary*. It does
# NOT boot a VM, enable microVM execution, or prove a working sandbox. The macOS
# VZ runner additionally requires a signed runner + a valid artifact manifest
# (see docs/adr/ADR-024-microvm-public-execution-contract.md), which remain
# operator-gated. microVM execution stays default-off and host-unproven.
#
# USAGE:
#   tools/build-arc-vz-busybox.sh [--output PATH] [--arch arm64|amd64] \
#                                 [--alpine-tag TAG]
#
#   --output PATH      Where to write the binary
#                      (default: $ARC_VZ_BUSYBOX or ~/.cache/arc/microvm/busybox)
#   --arch ARCH        Guest architecture: arm64 (Apple Silicon guest, default)
#                      or amd64
#   --alpine-tag TAG   Alpine image tag (default: 3.20)
#
# After building, point ARC at the binary and pack the initramfs:
#   export ARC_VZ_BUSYBOX=<output path>
#   cd python && uv run arc sandbox vz-artifacts --json --exec-init \
#       --pack-initrd --busybox "$ARC_VZ_BUSYBOX" --output /tmp/arc-vz-initrd
#
set -euo pipefail

ARCH="${ARC_VZ_BUSYBOX_ARCH:-arm64}"
ALPINE_TAG="${ARC_ALPINE_TAG:-3.20}"
OUTPUT="${ARC_VZ_BUSYBOX:-${HOME}/.cache/arc/microvm/busybox}"

while [ $# -gt 0 ]; do
  case "$1" in
    --output)
      OUTPUT="${2:?--output requires a path}"
      shift 2
      ;;
    --arch)
      ARCH="${2:?--arch requires arm64 or amd64}"
      shift 2
      ;;
    --alpine-tag)
      ALPINE_TAG="${2:?--alpine-tag requires a tag}"
      shift 2
      ;;
    -h | --help)
      sed -n '2,40p' "$0"
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

case "$ARCH" in
  arm64 | aarch64) PLATFORM="linux/arm64" ;;
  amd64 | x86_64) PLATFORM="linux/amd64" ;;
  *)
    echo "error: unsupported --arch '$ARCH' (use arm64 or amd64)" >&2
    exit 2
    ;;
esac

if ! command -v docker >/dev/null 2>&1; then
  cat >&2 <<'EOF'
error: docker is required to build a static Linux BusyBox from this macOS host.

Install Docker Desktop (or another Docker engine) and re-run. Alternatively,
supply your own static Linux BusyBox binary and point ARC_VZ_BUSYBOX at it; the
only hard requirement is that it is statically linked (no /lib/ld-musl or
/lib/ld-linux loader path) and matches the guest architecture.
EOF
  exit 3
fi

if ! docker info >/dev/null 2>&1; then
  echo "error: the Docker daemon is not reachable; start Docker Desktop/engine and re-run." >&2
  exit 3
fi

OUT_DIR="$(dirname "$OUTPUT")"
OUT_NAME="$(basename "$OUTPUT")"
mkdir -p "$OUT_DIR"

echo ">> building static BusyBox ($PLATFORM, alpine:$ALPINE_TAG) -> $OUTPUT"

# Run unprivileged; install the signed static package and copy the binary out.
docker run --rm --platform "$PLATFORM" \
  -v "$OUT_DIR:/out" \
  "alpine:$ALPINE_TAG" \
  sh -eu -c '
    apk add --no-cache busybox-static >/dev/null
    if [ ! -f /bin/busybox.static ]; then
      echo "error: /bin/busybox.static not found in alpine busybox-static" >&2
      exit 1
    fi
    cp /bin/busybox.static "/out/'"$OUT_NAME"'"
    chmod 0755 "/out/'"$OUT_NAME"'"
  '

if [ ! -f "$OUTPUT" ]; then
  echo "error: build did not produce $OUTPUT" >&2
  exit 1
fi

# Mirror isolation/vz_provider.py::_looks_static_linux_binary: reject a binary
# that embeds a dynamic-loader path (i.e. is not statically linked).
if LC_ALL=C grep -aq -e '/lib/ld-musl' -e '/lib64/ld-musl' \
  -e '/lib/ld-linux' -e '/lib64/ld-linux' "$OUTPUT"; then
  echo "error: produced binary is dynamically linked (has a loader path)" >&2
  exit 4
fi

SHA="$(shasum -a 256 "$OUTPUT" 2>/dev/null | awk '{print $1}' || true)"
echo ">> ok: static BusyBox written to $OUTPUT"
[ -n "$SHA" ] && echo ">> sha256: $SHA"
echo ">> next:"
echo "     export ARC_VZ_BUSYBOX=\"$OUTPUT\""
echo "     cd python && uv run arc sandbox vz-artifacts --json --exec-init \\"
echo "         --pack-initrd --busybox \"\$ARC_VZ_BUSYBOX\" --output /tmp/arc-vz-initrd"
