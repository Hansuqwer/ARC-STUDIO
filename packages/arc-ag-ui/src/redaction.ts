// Single source of redaction truth. Imported by trace exporter, AI variables,
// provider diagnostics, and the event stream view.

const SECRET_PATTERNS: RegExp[] = [
  /\b(sk-[A-Za-z0-9_-]{16,})\b/g,                      // OpenAI-style keys
  /\bxox[bpoas]-[A-Za-z0-9-]{10,}\b/g,                 // Slack tokens
  /\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b/g,     // GitHub tokens
  /\bAKIA[0-9A-Z]{16}\b/g,                             // AWS access keys
];

const SECRET_KEY_NAMES = new Set([
  'api_key', 'apikey', 'token', 'authorization', 'password',
  'secret', 'access_key', 'client_secret', 'bearer',
]);

export const MAX_EVENT_BYTES = 64 * 1024;
export const REDACTED = '«REDACTED»';

export function redactString(s: string): string {
  let out = s;
  for (const pat of SECRET_PATTERNS) out = out.replace(pat, REDACTED);
  return out;
}

export function redactValue(v: unknown, keyName?: string): unknown {
  if (keyName && SECRET_KEY_NAMES.has(keyName.toLowerCase())) return REDACTED;
  if (typeof v === 'string') return redactString(v);
  if (Array.isArray(v)) return v.map(item => redactValue(item));
  if (v && typeof v === 'object') {
    const out: Record<string, unknown> = {};
    for (const [k, val] of Object.entries(v)) out[k] = redactValue(val, k);
    return out;
  }
  return v;
}

export function capPayload<T>(v: T): T {
  const json = JSON.stringify(v);
  if (json.length <= MAX_EVENT_BYTES) return v;
  return JSON.parse(JSON.stringify({
    __truncated: true,
    __originalBytes: json.length,
    preview: json.slice(0, 2048),
  })) as T;
}

export function safeEvent<T extends object>(e: T): T {
  return capPayload(redactValue(e) as T);
}
