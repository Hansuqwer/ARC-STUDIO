//! Deterministic workload generators — every candidate opens the *same bytes*.
//! Seeded LCG (no rand dependency); generation is reproducible by construction
//! and verified by digest tests.

/// Minimal deterministic PRNG (Numerical Recipes LCG). Stable across platforms.
pub struct Lcg(u64);

impl Lcg {
    pub fn new(seed: u64) -> Self {
        Self(seed)
    }
    pub fn next_u32(&mut self) -> u32 {
        self.0 = self
            .0
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        (self.0 >> 33) as u32
    }
}

/// G1 workload A: `size_bytes` of plausible source-like lines (60–100 chars).
pub fn source_like(size_bytes: usize, seed: u64) -> String {
    const WORDS: &[&str] = &[
        "fn", "let", "match", "impl", "pub", "struct", "enum", "async", "await", "self", "return",
        "mut", "ref", "for", "while", "loop", "if", "else", "buffer", "editor", "render",
        "viewport", "daemon", "event", "stream",
    ];
    let mut rng = Lcg::new(seed);
    let mut out = String::with_capacity(size_bytes + 128);
    while out.len() < size_bytes {
        let indent = (rng.next_u32() % 4) as usize * 4;
        out.extend(std::iter::repeat_n(' ', indent));
        let words = 6 + (rng.next_u32() % 8) as usize;
        for i in 0..words {
            if i > 0 {
                out.push(' ');
            }
            out.push_str(WORDS[(rng.next_u32() as usize) % WORDS.len()]);
        }
        out.push('\n');
    }
    out.truncate(size_bytes);
    out
}

/// G1 workload B (pathological): one single line of `size_bytes` with no
/// newline — the case that kills naïve line-based viewports.
pub fn pathological_single_line(size_bytes: usize, seed: u64) -> String {
    let mut rng = Lcg::new(seed);
    let mut out = String::with_capacity(size_bytes);
    const CHUNK: &[u8] = b"{\"k\":0123456789abcdef,";
    while out.len() < size_bytes {
        let i = (rng.next_u32() as usize) % CHUNK.len();
        out.push(CHUNK[i] as char);
    }
    out.truncate(size_bytes);
    out
}

/// G2 workload: a unified diff with `lines` total +/- lines across hunks.
pub fn synthetic_diff(lines: usize, seed: u64) -> String {
    let mut rng = Lcg::new(seed);
    let mut out = String::new();
    out.push_str("--- a/src/big_module.rs\n+++ b/src/big_module.rs\n");
    let mut written = 0usize;
    let mut old_ln = 1usize;
    while written < lines {
        let hunk = (10 + rng.next_u32() % 40) as usize;
        out.push_str(&format!("@@ -{old_ln},{hunk} +{old_ln},{hunk} @@\n"));
        for _ in 0..hunk {
            if written >= lines {
                break;
            }
            let sign = if rng.next_u32().is_multiple_of(2) {
                '-'
            } else {
                '+'
            };
            out.push(sign);
            out.push_str(&format!(" line {written}: value = {};\n", rng.next_u32()));
            written += 1;
        }
        old_ln += hunk;
    }
    out
}

/// G4 workload: deterministic 2000-key synthetic typing stream (brief §3.5
/// instrumentation sketch sizes its sample buffer to 2000).
pub fn synthetic_keystream(seed: u64) -> Vec<char> {
    const KEYS: &[char] = &[
        'a', 'e', 'i', 'o', 'u', 't', 'n', 's', 'r', 'l', ' ', '(', ')', '{', '}', ';', ':', '.',
        ',', '_', '\n',
    ];
    let mut rng = Lcg::new(seed);
    (0..2000)
        .map(|_| KEYS[(rng.next_u32() as usize) % KEYS.len()])
        .collect()
}

/// Canonical seeds — fixed so every candidate, every machine, every rerun
/// opens identical workloads. Changing a seed is a reviewed diff.
pub mod seeds {
    pub const G1_SOURCE: u64 = 0xA5C_0001;
    pub const G1_PATHOLOGICAL: u64 = 0xA5C_0002;
    pub const G2_DIFF: u64 = 0xA5C_0003;
    pub const G4_KEYS: u64 = 0xA5C_0004;
}

/// FNV-1a digest for reproducibility checks (not cryptographic; drift detector).
pub fn fnv1a(bytes: &[u8]) -> u64 {
    let mut h: u64 = 0xcbf29ce484222325;
    for b in bytes {
        h ^= *b as u64;
        h = h.wrapping_mul(0x100000001b3);
    }
    h
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn workloads_are_deterministic() {
        assert_eq!(
            fnv1a(source_like(100_000, seeds::G1_SOURCE).as_bytes()),
            fnv1a(source_like(100_000, seeds::G1_SOURCE).as_bytes())
        );
        assert_ne!(
            fnv1a(source_like(100_000, 1).as_bytes()),
            fnv1a(source_like(100_000, 2).as_bytes())
        );
    }

    #[test]
    fn pathological_has_no_newlines_and_exact_size() {
        let s = pathological_single_line(1_000_000, seeds::G1_PATHOLOGICAL);
        assert_eq!(s.len(), 1_000_000);
        assert!(!s.contains('\n'));
    }

    #[test]
    fn diff_has_requested_change_lines() {
        let d = synthetic_diff(5000, seeds::G2_DIFF);
        let changes = d
            .lines()
            .filter(|l| l.starts_with('+') || l.starts_with('-'))
            .count();
        // +/- lines plus the two file-header lines (--- / +++).
        assert_eq!(changes, 5000 + 2);
    }

    #[test]
    fn keystream_is_2000_keys() {
        assert_eq!(synthetic_keystream(seeds::G4_KEYS).len(), 2000);
    }
}
