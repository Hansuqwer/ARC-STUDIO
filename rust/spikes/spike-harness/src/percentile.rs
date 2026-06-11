//! Percentile math — one implementation, property-tested, used by every gate.
//! Method: nearest-rank on the sorted sample (ceil(p*n)), the same convention
//! as the Sprint-1 RTT baseline, so numbers stay comparable across sprints.

#[derive(Debug, Clone, PartialEq, serde::Serialize, serde::Deserialize)]
pub struct Percentiles {
    pub n: usize,
    pub p50_us: u64,
    pub p95_us: u64,
    pub p99_us: u64,
    pub max_us: u64,
}

impl Percentiles {
    /// Compute from raw microsecond samples. Returns None on empty input —
    /// an empty sample set must never silently report zeros.
    pub fn from_us(samples: &[u64]) -> Option<Self> {
        if samples.is_empty() {
            return None;
        }
        let mut sorted = samples.to_vec();
        sorted.sort_unstable();
        let rank = |p: f64| {
            let idx = ((sorted.len() as f64) * p).ceil() as usize;
            sorted[idx.clamp(1, sorted.len()) - 1]
        };
        Some(Self {
            n: sorted.len(),
            p50_us: rank(0.50),
            p95_us: rank(0.95),
            p99_us: rank(0.99),
            max_us: sorted[sorted.len() - 1],
        })
    }

    /// Frames-equivalent at the recorded refresh rate (review §10.2: a 16 ms
    /// bar false-fails at 60 Hz and false-passes at 120 Hz unless reported
    /// in frames as well as ms).
    pub fn p99_frames(&self, refresh_hz: f64) -> f64 {
        (self.p99_us as f64 / 1_000_000.0) * refresh_hz
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_is_none_not_zeros() {
        assert!(Percentiles::from_us(&[]).is_none());
    }

    #[test]
    fn single_sample_all_percentiles_equal() {
        let p = Percentiles::from_us(&[42]).unwrap();
        assert_eq!((p.p50_us, p.p95_us, p.p99_us, p.max_us), (42, 42, 42, 42));
    }

    #[test]
    fn nearest_rank_known_values() {
        // 1..=100: p50 = 50, p95 = 95, p99 = 99 under nearest-rank.
        let v: Vec<u64> = (1..=100).collect();
        let p = Percentiles::from_us(&v).unwrap();
        assert_eq!((p.p50_us, p.p95_us, p.p99_us), (50, 95, 99));
    }

    #[test]
    fn order_independent() {
        let mut v: Vec<u64> = (1..=1000).collect();
        let a = Percentiles::from_us(&v).unwrap();
        v.reverse();
        let b = Percentiles::from_us(&v).unwrap();
        assert_eq!(a, b);
    }

    #[test]
    fn frames_conversion() {
        let p = Percentiles::from_us(&[16_600]).unwrap(); // 16.6 ms
        let frames_60 = p.p99_frames(60.0);
        assert!((frames_60 - 0.996).abs() < 0.01, "≈1 frame at 60 Hz: {frames_60}");
        let frames_120 = p.p99_frames(120.0);
        assert!((frames_120 - 1.992).abs() < 0.01, "≈2 frames at 120 Hz");
    }
}
