//! gen-workloads — materialize the deterministic spike workloads to disk.
//! Usage: gen-workloads <out-dir>
//! Writes digests.json alongside so any machine can verify byte-identity.

use spike_harness::workloads::{
    fnv1a, pathological_single_line, seeds, source_like, synthetic_diff,
};

fn main() -> std::io::Result<()> {
    let out = std::path::PathBuf::from(
        std::env::args().nth(1).unwrap_or_else(|| "spike-workloads".into()),
    );
    std::fs::create_dir_all(&out)?;
    let mut digests = serde_json::Map::new();

    // G1: 10 MB CI-class + 100 MB desktop-class source-like; 10 MB pathological.
    // (1 GB file-open belongs to B4 in the Sprint-11 sweep, not the spike.)
    for (name, content) in [
        ("g1-source-10mb.txt", source_like(10 << 20, seeds::G1_SOURCE)),
        ("g1-source-100mb.txt", source_like(100 << 20, seeds::G1_SOURCE)),
        ("g1-pathological-10mb-single-line.txt", pathological_single_line(10 << 20, seeds::G1_PATHOLOGICAL)),
        ("g2-diff-5k-lines.patch", synthetic_diff(5000, seeds::G2_DIFF)),
    ] {
        let path = out.join(name);
        std::fs::write(&path, &content)?;
        digests.insert(name.into(), serde_json::json!(format!("{:016x}", fnv1a(content.as_bytes()))));
        eprintln!("wrote {} ({} bytes)", path.display(), content.len());
    }

    std::fs::write(
        out.join("digests.json"),
        serde_json::to_string_pretty(&serde_json::Value::Object(digests))
            .map_err(std::io::Error::other)?,
    )?;
    eprintln!("digests.json written — verify with the same binary on the spike machine");
    Ok(())
}
