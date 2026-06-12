//! arc-shell — Sprint 2/K2 shell skeleton.
//!
//! The default build remains headless and framework-free:
//!
//!   arc-shell --smoke-exit          start, build model, probe daemon once, exit 0
//!                                    (the hyperfine cold-start target from the brief)
//!   arc-shell --headless-status     print the status rail + palette listing and exit
//!
//! K2 adds the native window entrypoint behind `--features framework-gpui`:
//!
//!   arc-shell --window              open the gpui shell chrome seeded from the
//!                                    Sprint-3 facade port
//!
//! Pixel/window evidence still belongs to the pinned M4/display run. Headless
//! execution may only verify argument handling, model wiring, and default gates.

use arc_daemon_client::DaemonClient;
use arc_shell::{await_healthy, DaemonState, ShellModel};
use arc_ui::theme::Theme;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Mode {
    SmokeExit,
    HeadlessStatus,
    Window,
}

fn mode_from_args(args: &[String]) -> Option<Mode> {
    if args.iter().any(|a| a == "--window") {
        Some(Mode::Window)
    } else if args.iter().any(|a| a == "--headless-status") {
        Some(Mode::HeadlessStatus)
    } else if args.iter().any(|a| a == "--smoke-exit") {
        Some(Mode::SmokeExit)
    } else {
        None
    }
}

fn print_usage() {
    eprintln!("arc-shell (ARC Studio v2 native shell)");
    eprintln!("usage: arc-shell --smoke-exit | --headless-status | --window");
    eprintln!("  --smoke-exit       build model, probe daemon once, exit");
    eprintln!("  --headless-status  print status rail and command palette seed");
    eprintln!("  --window           open native window (requires --features framework-gpui)");
}

fn model_with_daemon_probe() -> Result<ShellModel, std::process::ExitCode> {
    let mut model = ShellModel::new(Theme::from_env());

    // Probe the daemon once (non-fatal): producer-truth from day one — the
    // status rail must reflect real daemon state, never invent it.
    let rt = match tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    {
        Ok(rt) => rt,
        Err(e) => {
            eprintln!("runtime: {e}");
            return Err(std::process::ExitCode::FAILURE);
        }
    };
    let base = std::env::var("ARC_DAEMON_URL").unwrap_or_else(|_| "http://127.0.0.1:7777".into());
    model.ctx.daemon = match DaemonClient::new(&base) {
        Ok(client) => rt.block_on(async {
            if await_healthy(&client, std::time::Duration::from_secs(2)).await {
                DaemonState::Healthy
            } else {
                DaemonState::Degraded {
                    reason: "health probe timeout (2s)".into(),
                }
            }
        }),
        Err(e) => DaemonState::Degraded {
            reason: format!("bad daemon url: {e}"),
        },
    };

    Ok(model)
}

fn print_headless_status(model: &ShellModel) {
    println!("ARC Studio v2 — shell skeleton (headless)");
    println!("status rail: {}", model.status_rail());
    println!("regions: workspace | editor | dock | status (F6 cycles)");
    println!("commands ({}):", model.registry.len());
    for cmd in model.registry.iter() {
        let short = cmd.shortcut.map(|s| format!("  [{s}]")).unwrap_or_default();
        println!("  {} — {}{}", cmd.id.0, cmd.title, short);
    }
}

#[cfg(feature = "framework-gpui")]
fn run_window() -> std::process::ExitCode {
    let model = match model_with_daemon_probe() {
        Ok(model) => model,
        Err(code) => return code,
    };
    arc_shell::render_gpui::open_window(model);
    std::process::ExitCode::SUCCESS
}

#[cfg(not(feature = "framework-gpui"))]
fn run_window() -> std::process::ExitCode {
    eprintln!("arc-shell --window requires building with --features framework-gpui");
    std::process::ExitCode::from(2)
}

fn main() -> std::process::ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let Some(mode) = mode_from_args(&args) else {
        print_usage();
        return std::process::ExitCode::from(2);
    };

    if mode == Mode::Window {
        return run_window();
    }

    let model = match model_with_daemon_probe() {
        Ok(model) => model,
        Err(code) => return code,
    };

    if mode == Mode::HeadlessStatus {
        print_headless_status(&model);
    }

    std::process::ExitCode::SUCCESS
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    fn args(items: &[&str]) -> Vec<String> {
        items.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn parses_existing_headless_modes() {
        assert_eq!(mode_from_args(&args(&["--smoke-exit"])), Some(Mode::SmokeExit));
        assert_eq!(
            mode_from_args(&args(&["--headless-status"])),
            Some(Mode::HeadlessStatus)
        );
    }

    #[test]
    fn parses_window_mode_for_k2() {
        assert_eq!(mode_from_args(&args(&["--window"])), Some(Mode::Window));
        assert_eq!(
            mode_from_args(&args(&["--smoke-exit", "--window"])),
            Some(Mode::Window)
        );
    }

    #[test]
    fn rejects_missing_mode() {
        assert_eq!(mode_from_args(&[]), None);
    }
}
