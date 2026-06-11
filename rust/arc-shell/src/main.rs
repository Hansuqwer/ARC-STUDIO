//! arc-shell — Sprint 2 headless skeleton.
//!
//! No UI framework is selected yet (ADR-0002 spike = Sprint 3), so this binary
//! is the *model* of the shell plus daemon supervision, exercised two ways:
//!
//!   arc-shell --smoke-exit          start, build model, probe daemon once, exit 0
//!                                    (the hyperfine cold-start target from the brief)
//!   arc-shell --headless-status     print the status rail + palette listing and exit
//!
//! When Sprint 3 selects a framework, `arc_ui::kit` gains the renderer and this
//! main() grows a window; the model and tests stay identical.

use arc_daemon_client::DaemonClient;
use arc_shell::{await_healthy, DaemonState, ShellModel};
use arc_ui::theme::Theme;

fn main() -> std::process::ExitCode {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let smoke = args.iter().any(|a| a == "--smoke-exit");
    let headless = args.iter().any(|a| a == "--headless-status");
    if !smoke && !headless {
        eprintln!("arc-shell (Sprint 2 skeleton): pass --smoke-exit or --headless-status");
        eprintln!("window rendering lands with the Sprint-3 framework decision (ADR-0002)");
        return std::process::ExitCode::from(2);
    }

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
            return std::process::ExitCode::FAILURE;
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

    if headless {
        println!("ARC Studio v2 — shell skeleton (headless)");
        println!("status rail: {}", model.status_rail());
        println!("regions: workspace | editor | dock | status (F6 cycles)");
        println!("commands ({}):", model.registry.len());
        for cmd in model.registry.iter() {
            let short = cmd.shortcut.map(|s| format!("  [{s}]")).unwrap_or_default();
            println!("  {} — {}{}", cmd.id.0, cmd.title, short);
        }
    }
    std::process::ExitCode::SUCCESS
}
