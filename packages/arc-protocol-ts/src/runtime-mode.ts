/**
 * Canonical runtime mode enum for ARC Studio.
 * 
 * Lock: docs/adr/ADR-011-full-parity-framing.md
 * Phase: 3 (Runtime Semantics Unification)
 * 
 * Mirrors python/src/agent_runtime_cockpit/runtime/mode.py
 */

export enum RuntimeMode {
  /**
   * Deterministic stub responses, zero external calls, no gating required.
   * Cost source: 'estimated', value 0.0.
   */
  FAKE = 'fake',

  /**
   * Local model execution behind a gate.
   * Snake_case preserved for compatibility with on-disk session files.
   */
  GATED_LOCAL = 'gated_local',

  /**
   * External provider calls. Requires allow_paid_calls=true plus
   * provider-specific gates.
   */
  PROVIDER_BACKED = 'provider_backed',
}

const CANONICAL_VALUES = new Set<string>(['fake', 'gated_local', 'provider_backed']);

const LEGACY_MAP: Record<string, RuntimeMode> = {
  offline: RuntimeMode.FAKE,
  local: RuntimeMode.GATED_LOCAL,
  gated: RuntimeMode.GATED_LOCAL,
  live: RuntimeMode.PROVIDER_BACKED,
};

/**
 * Coerce a legacy mode string to the canonical enum.
 * 
 * Accepts:
 * - canonical strings: 'fake', 'gated_local', 'provider_backed'
 * - legacy strings: 'offline', 'local', 'gated', 'live'
 * - already-RuntimeMode instances (pass-through, no warning)
 * 
 * Throws Error on unknown values. Logs warning when a legacy string is supplied.
 */
export function fromLegacyRuntimeMode(value: string | RuntimeMode): RuntimeMode {
  if (typeof value !== 'string') {
    return value as RuntimeMode;
  }

  const normalized = value.trim().toLowerCase();

  // Canonical values: no warning, direct return
  if (CANONICAL_VALUES.has(normalized)) {
    return normalized as RuntimeMode;
  }

  // Legacy values: warn and map
  if (normalized in LEGACY_MAP) {
    const canonical = LEGACY_MAP[normalized];
    console.warn(
      `Legacy runtime mode '${value}' is deprecated; use '${canonical}' instead. ` +
      `This shim will be removed in Phase 6.`
    );
    return canonical;
  }

  throw new Error(
    `Unknown runtime mode: '${value}'. ` +
    `Valid values: ${Array.from(CANONICAL_VALUES).sort()} ` +
    `(legacy aliases: ${Object.keys(LEGACY_MAP).sort()})`
  );
}

/**
 * True if the mode requires allow_paid_calls=true to execute.
 */
export function isPaidMode(mode: RuntimeMode): boolean {
  return mode === RuntimeMode.PROVIDER_BACKED;
}
