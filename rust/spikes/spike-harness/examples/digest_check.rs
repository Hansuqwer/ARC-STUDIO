fn main() {
    use spike_harness::workloads::*;
    let a = fnv1a(source_like(10 << 20, seeds::G1_SOURCE).as_bytes());
    let b = fnv1a(source_like(10 << 20, seeds::G1_SOURCE).as_bytes());
    let p = fnv1a(pathological_single_line(10 << 20, seeds::G1_PATHOLOGICAL).as_bytes());
    println!("source-10mb digest {:016x} (stable: {})", a, a == b);
    println!("pathological-10mb digest {:016x}", p);
}
