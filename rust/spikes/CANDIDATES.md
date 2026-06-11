# Sprint-3 candidate spike crates — implementation contract

The harness owns ALL methodology: frame script order, warmups, percentiles,
gate bars, report format, raw-data files. A candidate owns one event loop and
one window. It calls `FrameScript::on_present(Instant::now())` from a trusted
present/frame-complete callback, applies the returned `Action` to the next
frame, and calls `assemble_report()` after `Action::Finished`. If you find
yourself writing percentile math or report JSON in a candidate crate, stop —
that belongs in `spike-harness`.

Pins (resolved 2026-06-11 by local preflight, macOS arm64 M4):

| Candidate | Pin |
|---|---|
| gpui | 0.2.2 (crates.io) |
| gpui-ce | rev c237d57d1caed1bb6c6651ddc3ce9cafa86161b6 |
| floem | 0.2.0 |
| bespoke | winit 0.31.0-beta.2, vello 0.9.0, parley 0.10.0, accesskit_winit 0.33.0, masonry 0.4.0 (optional widget layer) |

## FrameScript semantics — the traps

1. **Present-callback, not render-return.** G1/G4 measure to the frame
   *presented* on screen. gpui: `window.on_next_frame`. floem: tie to the
   next paint via `request_paint` + frame callback. bespoke: wgpu present
   timestamp / winit `RedrawRequested` completion. Measuring render-call
   return is the classic false-pass.
2. **One action per present.** `on_present` yields at most one `Action`; apply
   it once, then wait for the next trustworthy present/frame-complete callback.
3. **G3 is chunked arrival, not full batching.** `AppendRows` defaults to 10 rows
   per frame. Finding F9: one-row-per-frame makes the 250 ms total budget
   impossible at vsync, but all-rows-in-one-frame measures nothing. The script
   caps the chunk; the 33 ms worst-frame bar still polices rendering cost.
4. **No present callback, no approximation.** If a framework only exposes
   render-return, record that as candidate evidence and stop that candidate run.

## Evidence rows (G5/G6/G7/G8)

The runner writes them as EvidencePending. The operator completes them by
editing the committed `reports/spike-<candidate>.json`: replace the pending
outcome with `Pass` ONLY alongside artifact paths added to `raw_data_path` or
`notes`. Golden rule: an evidence row without a file path is still pending,
whatever its outcome field says — the decision matrix requires paths.
