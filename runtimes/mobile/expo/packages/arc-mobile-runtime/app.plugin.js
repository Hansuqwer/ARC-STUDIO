/**
 * ARC Mobile Runtime — Expo config plugin (advisory permission injection).
 *
 * SIMULATOR PREVIEW. This plugin declares, in an Expo app config, the OS permissions
 * that ARC's *simulated* capabilities would require on a real device. The native module
 * returns fixtures only and accesses no real device APIs (see app.plugin safety notes and
 * the forbidden-symbol CI gate). These declarations are ADVISORY: they let a developer see
 * the permission surface implied by their declared capabilities. They are NOT a grant of
 * real device access and MUST be reviewed by a human before any app-store submission.
 *
 * Usage (app.json / app.config.js):
 *   ["arc-mobile-runtime", { "permissions": ["ios.camera", "android.CAMERA"] }]
 *   ["arc-mobile-runtime", { "capabilities": [ <MobileCapability objects> ] }]
 *
 * Pure, dependency-free `(config, props) => config` transform so it is deterministic and
 * testable without the Expo toolchain.
 */
'use strict';

const PERMISSION_MAP = require('./plugin/arc-permission-map.json');

const ADVISORY =
  'ARC advisory (simulator preview): declared for the simulated capability only; ' +
  'no real device access is performed. Requires human review before store submission.';

/** Collect ARC permission IDs from either `permissions: string[]` or `capabilities[].required_permissions`. */
function collectPermissionIds(props) {
  const ids = new Set();
  if (props && Array.isArray(props.permissions)) {
    for (const p of props.permissions) if (typeof p === 'string') ids.add(p);
  }
  if (props && Array.isArray(props.capabilities)) {
    for (const cap of props.capabilities) {
      const reqs = (cap && cap.required_permissions) || [];
      for (const r of reqs) ids.add(typeof r === 'string' ? r : r && r.id);
    }
  }
  ids.delete(undefined);
  return [...ids].filter(Boolean).sort();
}

/**
 * Expo config plugin. Injects advisory iOS usage strings + Android permissions derived
 * from the ARC capability permission map. Unknown permission IDs are ignored (advisory
 * surface is allowlist-only). Deterministic: outputs are sorted and idempotent.
 */
function withArcMobileRuntime(config, props) {
  const ids = collectPermissionIds(props || {});

  config = config || {};
  config.ios = config.ios || {};
  config.ios.infoPlist = config.ios.infoPlist || {};
  config.android = config.android || {};
  const androidPerms = new Set(config.android.permissions || []);

  const injected = [];
  for (const id of ids) {
    const m = PERMISSION_MAP[id];
    if (!m) continue; // allowlist-only; unknown IDs are not injected
    if (m.platform === 'ios') {
      config.ios.infoPlist[m.manifestKey] = `${m.label}. ${ADVISORY}`;
      injected.push(id);
    } else if (m.platform === 'android') {
      androidPerms.add(m.manifestKey);
      injected.push(id);
    }
  }
  config.android.permissions = [...androidPerms].sort();

  config.extra = config.extra || {};
  config.extra.arcMobileRuntimeAdvisory = {
    simulatorPreview: true,
    note: ADVISORY,
    injectedPermissionIds: injected.sort(),
  };
  return config;
}

module.exports = withArcMobileRuntime;
module.exports.withArcMobileRuntime = withArcMobileRuntime;
module.exports.collectPermissionIds = collectPermissionIds;
module.exports.PERMISSION_MAP = PERMISSION_MAP;
module.exports.ADVISORY = ADVISORY;
