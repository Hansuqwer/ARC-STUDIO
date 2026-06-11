#![allow(clippy::unwrap_used)] // test code: panics are the failure mechanism
//! Sprint-1 fixture conformance gate.
//!
//! - Every fixture under `protocol/fixtures/{run-event,arc-envelope,error-codes,
//!   runtime-capabilities}/` must decode and re-encode to *semantic* equality
//!   (Value compare). Byte equality is claimed nowhere — the schema does not fix
//!   key order.
//! - The registry coverage test enumerates `eventTypes` from
//!   `run-event-registry.json`, asserts every fixture kind is registered, and
//!   writes the uncovered-kind list to `reports/fixture-coverage.md` — a finding,
//!   not a silent skip (review report §6.6 / F1).

use std::collections::BTreeSet;
use std::fs;
use std::path::PathBuf;

fn repo_root() -> PathBuf {
    // rust/arc-protocol-rs -> repo root
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .expect("repo root")
}

fn fixtures_root() -> PathBuf {
    repo_root().join("protocol/fixtures")
}

fn json_files(dir: &std::path::Path) -> Vec<PathBuf> {
    let mut v: Vec<PathBuf> = fs::read_dir(dir)
        .unwrap_or_else(|e| panic!("{}: {e}", dir.display()))
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("json"))
        .collect();
    v.sort();
    v
}

fn roundtrip<T: serde::de::DeserializeOwned + serde::Serialize>(raw: &str, ctx: &str) {
    let typed: T =
        serde_json::from_str(raw).unwrap_or_else(|e| panic!("{ctx}: decode failed: {e}"));
    let back = serde_json::to_value(&typed).unwrap_or_else(|e| panic!("{ctx}: re-encode: {e}"));
    let orig: serde_json::Value = serde_json::from_str(raw).expect("orig is valid json");
    assert_eq!(orig, back, "{ctx}: re-encode drift (semantic)");
}

#[test]
fn every_run_event_fixture_decodes_and_reencodes() {
    let dir = fixtures_root().join("run-event");
    let files = json_files(&dir);
    assert!(!files.is_empty(), "no run-event fixtures found");
    for p in &files {
        let raw = fs::read_to_string(p).unwrap();
        roundtrip::<arc_protocol_rs::RunEvent>(&raw, &p.display().to_string());
    }
    println!("run-event fixtures decoded: {}", files.len());
}

#[test]
fn every_arc_envelope_fixture_decodes_and_reencodes() {
    for p in json_files(&fixtures_root().join("arc-envelope")) {
        let raw = fs::read_to_string(&p).unwrap();
        roundtrip::<arc_protocol_rs::ArcEnvelope<serde_json::Value>>(
            &raw,
            &p.display().to_string(),
        );
        // into_result() must never panic and must obey ok/error semantics.
        let env: arc_protocol_rs::ArcEnvelope<serde_json::Value> =
            serde_json::from_str(&raw).unwrap();
        let ok = env.ok;
        match env.into_result() {
            Ok(_) => assert!(ok, "{}: ok=false decoded as Ok", p.display()),
            Err(e) => {
                assert!(!ok, "{}: ok=true decoded as Err", p.display());
                assert!(!e.code.is_empty());
            }
        }
    }
}

#[test]
fn error_code_fixtures_decode_as_arc_error() {
    // error-codes/*.json may be bare ArcError objects or envelopes; inspect shape.
    for p in json_files(&fixtures_root().join("error-codes")) {
        let raw = fs::read_to_string(&p).unwrap();
        let v: serde_json::Value = serde_json::from_str(&raw).unwrap();
        let ctx = p.display().to_string();
        if v.get("ok").is_some() {
            roundtrip::<arc_protocol_rs::ArcEnvelope<serde_json::Value>>(&raw, &ctx);
        } else if v.get("code").is_some() {
            roundtrip::<arc_protocol_rs::ArcError>(&raw, &ctx);
        } else {
            panic!("{ctx}: unrecognized error-code fixture shape (finding, not skip)");
        }
    }
}

#[test]
fn runtime_capabilities_fixtures_are_valid_json_objects() {
    // No typed mirror yet (Sprint-1 scope is envelope+run-event); assert valid
    // JSON objects so additions/corruption are caught. Typed mirror = Sprint 2+.
    for p in json_files(&fixtures_root().join("runtime-capabilities")) {
        let raw = fs::read_to_string(&p).unwrap();
        let v: serde_json::Value =
            serde_json::from_str(&raw).unwrap_or_else(|e| panic!("{}: {e}", p.display()));
        assert!(v.is_object(), "{}: not an object", p.display());
    }
}

#[test]
fn registry_coverage_is_enumerated_and_reported() {
    let reg_raw = fs::read_to_string(fixtures_root().join("run-event-registry.json")).unwrap();
    let reg: serde_json::Value = serde_json::from_str(&reg_raw).unwrap();

    // Verified registry shape: {schemaVersion, source, eventTypes:[{type,version,requiredFields,optionalFields}]}
    let kinds: BTreeSet<String> = reg["eventTypes"]
        .as_array()
        .expect("eventTypes array")
        .iter()
        .map(|e| e["type"].as_str().expect("type string").to_owned())
        .collect();
    assert!(
        kinds.len() >= 60,
        "registry unexpectedly small: {} kinds",
        kinds.len()
    );

    // Kinds present in fixtures (decoded, not filename-derived).
    let mut fixture_kinds = BTreeSet::new();
    for p in json_files(&fixtures_root().join("run-event")) {
        let ev: arc_protocol_rs::RunEvent =
            serde_json::from_str(&fs::read_to_string(&p).unwrap()).unwrap();
        fixture_kinds.insert(ev.kind);
    }

    // HARD GATE: every fixture kind must be registered (inverse may lag).
    let unregistered: Vec<_> = fixture_kinds.difference(&kinds).collect();
    assert!(
        unregistered.is_empty(),
        "fixture kinds missing from registry: {unregistered:?}"
    );

    // FINDING (not a failure): registered kinds without fixtures, committed to reports/.
    let uncovered: Vec<_> = kinds.difference(&fixture_kinds).cloned().collect();
    let reports = repo_root().join("reports");
    fs::create_dir_all(&reports).unwrap();
    let mut md = String::new();
    md.push_str("# Run-event fixture coverage (generated by arc-protocol-rs tests)\n\n");
    md.push_str(&format!(
        "- Registered kinds: **{}**\n- Kinds with >=1 decoding fixture: **{}**\n- Uncovered kinds: **{}**\n\n",
        kinds.len(),
        fixture_kinds.len(),
        uncovered.len()
    ));
    md.push_str("Uncovered kinds decode via `KnownRunEvent::Unknown` (forward-compatible), but are unrendered and untested. Owner decision Q10 (review report §17.2) governs which families get additive daemon-side fixtures before the panels that render them.\n\n## Uncovered\n\n");
    for k in &uncovered {
        md.push_str(&format!("- `{k}`\n"));
    }
    md.push_str("\n## Covered\n\n");
    for k in &fixture_kinds {
        md.push_str(&format!("- `{k}`\n"));
    }
    fs::write(reports.join("fixture-coverage.md"), md).unwrap();
    println!(
        "coverage: {}/{} kinds have fixtures; report written",
        fixture_kinds.len(),
        kinds.len()
    );
}

#[test]
fn unknown_kind_and_unknown_fields_are_tolerated() {
    // Additive-protocol rule, tested explicitly.
    let raw = r#"{
        "schema_version": 3,
        "type": "SOME_FUTURE_EVENT",
        "timestamp": "2026-06-11T12:00:00.000Z",
        "run_id": "01HV7B3S0K9N3W2Q5J4Y8A6C2P",
        "sequence": 7,
        "data": {"anything": true},
        "brand_new_top_level_field": {"nested": [1,2,3]}
    }"#;
    let ev: arc_protocol_rs::RunEvent = serde_json::from_str(raw).expect("unknowns tolerated");
    assert_eq!(ev.kind, "SOME_FUTURE_EVENT");
    assert!(ev.extra.contains_key("brand_new_top_level_field"));
    match arc_protocol_rs::KnownRunEvent::from(ev) {
        arc_protocol_rs::KnownRunEvent::Unknown(e) => {
            // Re-encode keeps the unknown field — additive round-trip.
            let back = serde_json::to_value(&e).unwrap();
            assert!(back.get("brand_new_top_level_field").is_some());
        }
        other => panic!("expected Unknown, got {other:?}"),
    }
}

#[test]
fn ok_false_without_error_is_a_protocol_violation() {
    let raw = r#"{"version":"1.0","ok":false,"data":null,"error":null,"meta":null}"#;
    let env: arc_protocol_rs::ArcEnvelope<serde_json::Value> = serde_json::from_str(raw).unwrap();
    let err = env.into_result().unwrap_err();
    assert_eq!(err.code, "PROTOCOL_VIOLATION");
}
