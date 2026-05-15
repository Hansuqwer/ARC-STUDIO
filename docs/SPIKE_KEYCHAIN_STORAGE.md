# Spike: Secret Storage via keyring (ADR-005)

**Date:** 2026-05-15  
**Platform tested:** macOS (arm64)  
**Library:** `keyring` 25.7.0  

## Summary

`keyring` works on macOS via the macOS Keychain backend. Set/get/delete operations
succeed. Missing keys return `None`. No `__version__` attribute on the module.

## Recommendations

1. **Do NOT add `keyring` as a dependency yet.** ADR-005 (audit key management)
   is planned for P2. Keep `keyring` as an optional dependency until the
   audit chain implementation (P2) requires it.
2. **Env fallback strategy:** When `keyring` is unavailable, fall back to
   `ARC_HMAC_KEY` env var with a degraded-status warning.
3. **Platform caveats:**
   - macOS: Works (Keychain)
   - Linux: `keyring` uses Secret Service (requires `dbus` + `gnome-keyring`
     or `keepassxc`). May fail in headless/CI environments.
   - Windows: Uses Credential Locker (untested in this spike).
4. **Implementation pattern:** 
   ```python
   try:
       import keyring
       key = keyring.get_password("arc-studio", "hmac-key")
   except Exception:
       key = os.environ.get("ARC_HMAC_KEY")
       if not key:
           raise RuntimeError("No HMAC key found (keyring + env fallback)")
   ```

## Post-Spike Cleanup

`keyring` has been uninstalled from the project venv after testing.
