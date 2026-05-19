#!/usr/bin/env bash
# ─── ARC Studio Electron Packaging Spike (ADR-008 Phase 1) ─────────────────
#
# Compares three daemon-bundling options:
#   A: PyInstaller (single binary)
#   B: Embedded Python + pip
#   C: uv-based bootstrap
#
# This is a measurement/validation spike only — it does NOT sign or publish.
# Run from the repo root.
set -euo pipefail

SPIKE_DIR="$(mktemp -d)"
echo "=== ARC Packaging Spike ==="
echo "Spike workdir: ${SPIKE_DIR}"
echo ""

cleanup() {
  rm -rf "${SPIKE_DIR}"
}
trap cleanup EXIT

RESULTS_FILE="${SPIKE_DIR}/spike-results.json"

# ─── Helper: measure size and time ─────────────────────────────────────────
measure() {
  local label="$1" ; shift
  local start
  start="$(date +%s)"
  echo "  [${label}] Starting..."
  "$@" 2>&1
  local rc=$?
  local elapsed=$(( $(date +%s) - start ))
  echo "  [${label}] Exit code: ${rc}, Duration: ${elapsed}s"
  return ${rc}
}

# ─── Helper: collect results ────────────────────────────────────────────────
RESULTS='{"options":[],"errors":[]}'

record() {
  local option="$1" status="$2" size="$3" duration="$4" note="$5"
  RESULTS=$(echo "${RESULTS}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
d['options'].append({
  'option': '${option}',
  'status': '${status}',
  'size_bytes': ${size:-0},
  'duration_s': ${duration:-0},
  'note': '''${note}'''
})
print(json.dumps(d))
")
}

record_error() {
  local option="$1" error="$2"
  RESULTS=$(echo "${RESULTS}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
d['errors'].append({
  'option': '${option}',
  'error': '''${error}'''
})
print(json.dumps(d))
")
}

# ─── Option A: PyInstaller ─────────────────────────────────────────────────
echo "--- Option A: PyInstaller single binary ---"
A_START="$(date +%s)"
A_STATUS="not_attempted"
A_SIZE=0
A_NOTE=""

if command -v pyinstaller &>/dev/null; then
  A_DIR="${SPIKE_DIR}/pyinstaller"
  mkdir -p "${A_DIR}"
  cd python
  if PYTHONWARNINGS=ignore pyinstaller \
    --name arc-daemon \
    --onefile \
    --distpath "${A_DIR}/dist" \
    --workpath "${A_DIR}/build" \
    --specpath "${A_DIR}" \
    --hidden-import aiohttp \
    --hidden-import aiofiles \
    --hidden-import pydantic \
    --hidden-import typer \
    --hidden-import rich \
    --hidden-import yaml \
    --hidden-import httpx \
    src/agent_runtime_cockpit/daemon.py 2>&1; then
    cd "${OLDPWD}"
    A_BINARY="${A_DIR}/dist/arc-daemon"
    if [ -f "${A_BINARY}" ]; then
      A_SIZE=$(stat -f%z "${A_BINARY}" 2>/dev/null || stat --format=%s "${A_BINARY}" 2>/dev/null || echo 0)
      A_STATUS="completed"
      A_NOTE="PyInstaller onefile binary created at ${A_BINARY}"
      echo "  Binary size: ${A_SIZE} bytes"
    else
      A_STATUS="failed_no_binary"
      A_NOTE="PyInstaller ran but produced no binary"
    fi
  else
    cd "${OLDPWD}"
    A_STATUS="failed"
    A_NOTE="PyInstaller build failed"
  fi
else
  A_STATUS="skipped"
  A_NOTE="PyInstaller not installed"
fi

A_ELAPSED=$(( $(date +%s) - A_START ))
record "A" "${A_STATUS}" "${A_SIZE}" "${A_ELAPSED}" "${A_NOTE}"
echo ""

# ─── Option B: Embedded Python venv ─────────────────────────────────────────
echo "--- Option B: Embedded Python venv ---"
B_START="$(date +%s)"
B_STATUS="not_attempted"
B_SIZE=0
B_NOTE=""

B_DIR="${SPIKE_DIR}/embedded-python"
mkdir -p "${B_DIR}/python"

# Create a minimal venv and install the package
if python3 -m venv "${B_DIR}/python/venv" 2>&1; then
  B_PIP="${B_DIR}/python/venv/bin/pip"
  if [ -f "${B_DIR}/python/venv/Scripts/pip" ]; then
    B_PIP="${B_DIR}/python/venv/Scripts/pip"
  fi
  # Install the local package
  if "${B_PIP}" install -e python/ 2>&1; then
    B_VENV_SIZE=$(du -sb "${B_DIR}/python/venv" 2>/dev/null | cut -f1 || echo 0)
    B_SIZE=${B_VENV_SIZE}
    B_STATUS="completed"
    B_NOTE="Embedded Python venv created at ${B_DIR}/python/venv"
    echo "  Venv size: ${B_SIZE} bytes"
  else
    B_STATUS="failed"
    B_NOTE="pip install failed"
  fi
else
  B_STATUS="failed"
  B_NOTE="venv creation failed"
fi

B_ELAPSED=$(( $(date +%s) - B_START ))
record "B" "${B_STATUS}" "${B_SIZE}" "${B_ELAPSED}" "${B_NOTE}"
echo ""

# ─── Option C: uv bootstrap ─────────────────────────────────────────────────
echo "--- Option C: uv bootstrap ---"
C_START="$(date +%s)"
C_STATUS="not_attempted"
C_SIZE=0
C_NOTE=""

C_DIR="${SPIKE_DIR}/uv-bootstrap"
mkdir -p "${C_DIR}/daemon"

if command -v uv &>/dev/null; then
  # Copy pyproject.toml and uv.lock
  cp python/pyproject.toml "${C_DIR}/daemon/"
  if [ -f python/uv.lock ]; then
    cp python/uv.lock "${C_DIR}/daemon/"
  else
    echo "  [WARNING] No uv.lock found; uv sync may need --no-lock"
  fi

  # Try uv sync
  if UV_PROJECT_ENVIRONMENT="${C_DIR}/daemon/.venv" uv sync --directory "${C_DIR}/daemon" --no-dev 2>&1; then
    C_VENV_SIZE=$(du -sb "${C_DIR}/daemon/.venv" 2>/dev/null | cut -f1 || echo 0)
    C_SIZE=${C_VENV_SIZE}
    C_STATUS="completed"
    C_NOTE="uv bootstrap created at ${C_DIR}/daemon"
    echo "  Venv size: ${C_SIZE} bytes"
  else
    C_STATUS="failed"
    C_NOTE="uv sync failed"
  fi
else
  C_STATUS="skipped"
  C_NOTE="uv not installed"
fi

C_ELAPSED=$(( $(date +%s) - C_START ))
record "C" "${C_STATUS}" "${C_SIZE}" "${C_ELAPSED}" "${C_NOTE}"
echo ""

# ─── Summary ────────────────────────────────────────────────────────────────
echo "=== Spike Results ==="
echo "${RESULTS}" | python3 -m json.tool
echo "${RESULTS}" > "${RESULTS_FILE}"
echo ""
echo "Results saved to: ${RESULTS_FILE}"

# Determine recommendation
COMPLETED=$(echo "${RESULTS}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
completed = [o for o in d['options'] if o['status'] == 'completed']
print(len(completed))
")

echo "=== Recommendation ==="
if [ "${COMPLETED}" -gt 0 ]; then
  echo "At least one bundling option completed successfully."
  echo "See ADR-008 for the phased approach:"
  echo "  Phase 1: Packaging spike (this script)"
  echo "  Phase 2: Embedded Python (recommended for maintenance)"
  echo "  Phase 3: uv bootstrap (recommended for DX)"
  echo ""
  echo "Per ADR-008, the recommended approach is:"
  echo "  Phase 1 → PyInstaller (quick) or embedded Python (maintainable)"
  echo "  Phase 2 → Embedded Python + pip"
  echo "  Phase 3 → uv-based bootstrap"
else
  echo "No bundling options completed. Install required tools and re-run."
  echo "  - PyInstaller: pip install pyinstaller"
  echo "  - uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
