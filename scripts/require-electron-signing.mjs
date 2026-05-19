import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { platform } from 'node:process';

const SIGNING_ENVS = ['CSC_LINK', 'CSC_KEY_PASSWORD'];
const API_KEY_ENVS = ['APPLE_API_KEY_PATH', 'APPLE_API_KEY_ID', 'APPLE_API_ISSUER_ID'];
const LEGACY_APPLE_ID_ENVS = ['APPLE_ID', 'APPLE_APP_SPECIFIC_PASSWORD', 'APPLE_TEAM_ID'];
const PHASE = process.env.ARC_SIGNING_PREFLIGHT_PHASE || 'pre-import';
const RELEASE_CONFIG_PATH = new URL('../applications/electron/electron-builder.release.yml', import.meta.url);

function envShape(env = process.env) {
  const missing = [...SIGNING_ENVS, ...API_KEY_ENVS].filter(name => !env[name]);
  const legacyPresent = LEGACY_APPLE_ID_ENVS.filter(name => Boolean(env[name]));
  return {
    ok: missing.length === 0,
    csc_present: SIGNING_ENVS.every(name => Boolean(env[name])),
    notarize_auth_strategy: API_KEY_ENVS.every(name => Boolean(env[name])) ? 'api_key' : null,
    notarize_auth_complete: API_KEY_ENVS.every(name => Boolean(env[name])),
    missing_envs: missing,
    ignored_envs: legacyPresent,
  };
}

function runTool(command, args) {
  try {
    const output = execFileSync(command, args, { encoding: 'utf8', timeout: 5000, stdio: ['ignore', 'pipe', 'pipe'] });
    return { ok: true, version: firstLine(output) };
  } catch (error) {
    return { ok: false, stderrTail: redact(tail(String(error.stderr || error.message || ''))) };
  }
}

function toolingCheck() {
  if (platform !== 'darwin') {
    return { ok: true, skipped: 'not-darwin' };
  }
  const notarytool = runTool('xcrun', ['notarytool', '--version']);
  const stapler = runTool('xcrun', ['-f', 'stapler']);
  const codesign = runTool('xcrun', ['-f', 'codesign']);
  return {
    ok: notarytool.ok && stapler.ok && codesign.ok,
    notarytool,
    stapler,
    codesign,
  };
}

function releaseConfigCheck() {
  let config;
  try {
    config = readFileSync(RELEASE_CONFIG_PATH, 'utf8');
  } catch (error) {
    return { ok: false, reason: 'release-config-missing', detail: redact(String(error.message || error)) };
  }

  const required = [
    { key: 'forceCodeSigning', pattern: /^forceCodeSigning:\s*true\s*$/m },
    { key: 'mac.hardenedRuntime', pattern: /^\s{2}hardenedRuntime:\s*true\s*$/m },
    { key: 'mac.gatekeeperAssess', pattern: /^\s{2}gatekeeperAssess:\s*false\s*$/m },
    { key: 'win.verifyUpdateCodeSignature', pattern: /^\s{2}verifyUpdateCodeSignature:\s*true\s*$/m },
    { key: 'win.signAndEditExecutable', pattern: /^\s{2}signAndEditExecutable:\s*true\s*$/m },
    { key: 'win.requestedExecutionLevel', pattern: /^\s{2}requestedExecutionLevel:\s*"asInvoker"\s*$/m },
  ];
  const missing = required.filter(item => !item.pattern.test(config)).map(item => item.key);
  return { ok: missing.length === 0, missing_keys: missing };
}

function certificateCheck(phase = PHASE) {
  if (platform !== 'darwin') {
    return { ok: true, skipped: 'not-darwin' };
  }
  const identity = findDeveloperIdIdentity();
  if (!identity) {
    return phase === 'post-import'
      ? { ok: false, reason: 'no-developer-id-identity' }
      : { ok: true, skipped: 'no-identity-yet' };
  }
  const expiry = certificateExpiry(identity.commonName);
  if (!expiry.ok) {
    return { ok: false, identity_subject_cn: identity.commonName, reason: expiry.reason };
  }
  return {
    ok: expiry.days_until_expiry >= 0,
    identity_subject_cn: identity.commonName,
    expires_at: expiry.expires_at,
    days_until_expiry: expiry.days_until_expiry,
    warning: expiry.days_until_expiry < 30 ? 'expires_soon' : null,
  };
}

function findDeveloperIdIdentity() {
  try {
    const output = execFileSync('security', ['find-identity', '-v', '-p', 'codesigning'], { encoding: 'utf8', timeout: 5000, stdio: ['ignore', 'pipe', 'pipe'] });
    const line = output.split('\n').find(item => item.includes('Developer ID Application:'));
    const match = line?.match(/"([^"]+)"/);
    return match ? { commonName: match[1] } : null;
  } catch {
    return null;
  }
}

function certificateExpiry(commonName) {
  try {
    const pem = execFileSync('security', ['find-certificate', '-c', commonName, '-p'], { encoding: 'utf8', timeout: 5000, stdio: ['ignore', 'pipe', 'pipe'] });
    const output = execFileSync('openssl', ['x509', '-noout', '-enddate'], { input: pem, encoding: 'utf8', timeout: 5000, stdio: ['pipe', 'pipe', 'pipe'] });
    const dateText = output.trim().replace(/^notAfter=/, '');
    const expires = new Date(dateText);
    if (Number.isNaN(expires.getTime())) {
      return { ok: false, reason: 'expiry-parse-failed' };
    }
    return {
      ok: true,
      expires_at: expires.toISOString(),
      days_until_expiry: Math.floor((expires.getTime() - Date.now()) / 86400000),
    };
  } catch {
    return { ok: false, reason: 'expiry-check-failed' };
  }
}

function preflight(env = process.env) {
  const envResult = envShape(env);
  const releaseConfig = releaseConfigCheck();
  const tooling = toolingCheck();
  const cert = certificateCheck();
  const warnings = [];
  if (envResult.ignored_envs.length > 0) {
    warnings.push({ code: 'legacy-apple-id-env-ignored', envs: envResult.ignored_envs });
  }
  if (cert.warning) {
    warnings.push({ code: cert.warning });
  }
  const exitCode = !releaseConfig.ok ? 40 : !envResult.ok ? 10 : !tooling.ok ? 20 : !cert.ok ? 30 : 0;
  return {
    platform,
    phase: PHASE,
    checks: {
      env_shape: envResult,
      release_config: releaseConfig,
      tooling,
      cert,
    },
    warnings,
    exit_code: exitCode,
  };
}

function firstLine(value) {
  return value.trim().split('\n')[0] || '';
}

function tail(value, n = 2048) {
  return value.length <= n ? value : value.slice(value.length - n);
}

function redact(value) {
  return value
    .replace(/sk-[A-Za-z0-9_-]{6,}/g, 'sk-***redacted***')
    .replace(/(app(?:lication)?[-_ ]?specific[-_ ]?password\s*[=:]\s*)\S+/gi, '$1***redacted***')
    .replace(/(p12|pkcs12|api[-_]?key|password)(\s*[=:]\s*)\S+/gi, '$1$2***redacted***');
}

const result = preflight();
console.log(JSON.stringify(result, null, 2));
if (result.exit_code !== 0) {
  console.error('Use package:smoke/package:dir for unsigned local smoke builds.');
  process.exit(result.exit_code);
}
