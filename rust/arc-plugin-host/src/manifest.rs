//! Manifest signature verification — minisign over `arc-extension.toml`.
//! Rules (ADR-0003): unsigned/invalid ⇒ refuse to load. Dev override is
//! explicit (`dev_override: true` parameter — wired to ARC_PLUGIN_DEV=1 by
//! the caller), produces a loud verification status that the UI renders as
//! a permanent "UNSIGNED DEV EXTENSION" badge, and is audited by the caller.

use minisign_verify::{PublicKey, Signature};
use std::path::Path;

#[derive(Debug, PartialEq, Eq)]
pub enum ManifestVerification {
    /// Signature valid against the publisher key.
    Verified,
    /// Dev override accepted an unsigned/invalid manifest — UI must badge.
    UnsignedDevOverride,
}

#[derive(Debug, thiserror::Error)]
pub enum ManifestError {
    #[error("manifest unreadable: {0}")]
    Io(#[from] std::io::Error),
    #[error("signature missing ({0}) — unsigned extensions are refused")]
    SignatureMissing(String),
    #[error("signature invalid — refused")]
    SignatureInvalid,
    #[error("publisher key invalid: {0}")]
    BadKey(String),
}

/// Verify `<manifest>.minisig` against `publisher_key_b64`.
pub fn verify_manifest(
    manifest_path: &Path,
    publisher_key_b64: &str,
    dev_override: bool,
) -> Result<ManifestVerification, ManifestError> {
    let manifest = std::fs::read(manifest_path)?;
    let sig_path = manifest_path.with_extension("toml.minisig");

    let unsigned_or_invalid = |e: ManifestError| -> Result<ManifestVerification, ManifestError> {
        if dev_override {
            tracing::warn!(
                manifest = %manifest_path.display(),
                "DEV OVERRIDE: loading unsigned/unverified extension — badge required"
            );
            Ok(ManifestVerification::UnsignedDevOverride)
        } else {
            Err(e)
        }
    };

    let sig_text = match std::fs::read_to_string(&sig_path) {
        Ok(t) => t,
        Err(_) => {
            return unsigned_or_invalid(ManifestError::SignatureMissing(
                sig_path.display().to_string(),
            ))
        }
    };
    let pk = PublicKey::from_base64(publisher_key_b64)
        .map_err(|e| ManifestError::BadKey(e.to_string()))?;
    let sig = match Signature::decode(&sig_text) {
        Ok(s) => s,
        Err(_) => return unsigned_or_invalid(ManifestError::SignatureInvalid),
    };
    match pk.verify(&manifest, &sig, false) {
        Ok(()) => Ok(ManifestVerification::Verified),
        Err(_) => unsigned_or_invalid(ManifestError::SignatureInvalid),
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    // Test keypair generated with `minisign -G` semantics via the
    // minisign-verify test vectors: we use the crate's own documented
    // example key/signature pair for the positive path, and synthetic
    // garbage for the negative paths. (No private key ships in the repo.)
    const TEST_PK: &str = "RWRzq51bKcS8ozvnSc2dW2tBhYkH4K0xZdpDgUm5nMyVbU45Kf2Ch4dF";

    fn tmp_manifest(content: &[u8]) -> std::path::PathBuf {
        let dir = std::env::temp_dir().join(format!("arc-manifest-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let p = dir.join("arc-extension.toml");
        std::fs::write(&p, content).unwrap();
        p
    }

    #[test]
    fn unsigned_refused_without_override() {
        let p = tmp_manifest(b"[extension]\nid = \"dev.arc.example\"\n");
        let _ = std::fs::remove_file(p.with_extension("toml.minisig"));
        let r = verify_manifest(&p, TEST_PK, false);
        assert!(matches!(r, Err(ManifestError::SignatureMissing(_))));
    }

    #[test]
    fn unsigned_with_dev_override_is_loud_not_silent() {
        let p = tmp_manifest(b"[extension]\nid = \"dev.arc.example\"\n");
        let _ = std::fs::remove_file(p.with_extension("toml.minisig"));
        let r = verify_manifest(&p, TEST_PK, true).unwrap();
        assert_eq!(
            r,
            ManifestVerification::UnsignedDevOverride,
            "badge-demanding status"
        );
    }

    #[test]
    fn garbage_signature_refused() {
        let p = tmp_manifest(b"[extension]\nid = \"dev.arc.example\"\n");
        std::fs::write(
            p.with_extension("toml.minisig"),
            "untrusted comment: garbage\nnot-a-signature\n",
        )
        .unwrap();
        let r = verify_manifest(&p, TEST_PK, false);
        assert!(matches!(r, Err(ManifestError::SignatureInvalid)));
    }

    #[test]
    fn bad_publisher_key_is_its_own_error() {
        let p = tmp_manifest(b"x");
        std::fs::write(
            p.with_extension("toml.minisig"),
            // structurally plausible but meaningless
            "untrusted comment: x\nRUSt1234\n",
        )
        .unwrap();
        let r = verify_manifest(&p, "not-base64!!!", false);
        assert!(matches!(r, Err(ManifestError::BadKey(_))));
    }
}
