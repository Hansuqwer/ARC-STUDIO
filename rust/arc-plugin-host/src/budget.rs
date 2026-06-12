//! Engine budgets — fuel (CPU) + epoch (wall clock), both deterministic
//! kills. Probe-verified in this container before adoption (2026-06-12).
//!
//! These are guest-side budgets; they complement, never replace, the
//! host-side timeouts in `host_call` (the brief's explicit warning).

use std::time::Duration;

#[derive(Debug, PartialEq, Eq)]
pub enum BudgetKill {
    FuelExhausted,
    EpochDeadline,
}

#[derive(Debug, thiserror::Error)]
pub enum EngineError {
    #[error("wasmtime: {0}")]
    Wasmtime(String),
}

pub struct PluginEngine {
    engine: wasmtime::Engine,
}

impl PluginEngine {
    pub fn new() -> Result<Self, EngineError> {
        let mut cfg = wasmtime::Config::new();
        cfg.consume_fuel(true).epoch_interruption(true);
        Ok(Self {
            engine: wasmtime::Engine::new(&cfg)
                .map_err(|e| EngineError::Wasmtime(e.to_string()))?,
        })
    }

    pub fn engine(&self) -> &wasmtime::Engine {
        &self.engine
    }

    /// Run `wat` export `entry` under the given budgets. Returns the value
    /// or the budget kill that stopped it. The epoch ticker is a real
    /// background thread (production shape), not a test shortcut.
    pub fn run_with_budgets(
        &self,
        wat: &str,
        entry: &str,
        fuel: u64,
        wall: Duration,
        tick: Duration,
    ) -> Result<Result<i32, BudgetKill>, EngineError> {
        let module = wasmtime::Module::new(&self.engine, wat)
            .map_err(|e| EngineError::Wasmtime(e.to_string()))?;
        let mut store = wasmtime::Store::new(&self.engine, ());
        store
            .set_fuel(fuel)
            .map_err(|e| EngineError::Wasmtime(e.to_string()))?;
        let deadline_ticks = (wall.as_millis() / tick.as_millis().max(1)).max(1) as u64;
        store.set_epoch_deadline(deadline_ticks);

        // background ticker (stops via flag when the call returns)
        let stop = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));
        let stop2 = stop.clone();
        let engine2 = self.engine.clone();
        let ticker = std::thread::spawn(move || {
            while !stop2.load(std::sync::atomic::Ordering::Relaxed) {
                std::thread::sleep(tick);
                engine2.increment_epoch();
            }
        });

        let result = (|| {
            let instance = wasmtime::Instance::new(&mut store, &module, &[])
                .map_err(|e| EngineError::Wasmtime(e.to_string()))?;
            let f = instance
                .get_typed_func::<(), i32>(&mut store, entry)
                .map_err(|e| EngineError::Wasmtime(e.to_string()))?;
            Ok::<_, EngineError>(match f.call(&mut store, ()) {
                Ok(v) => Ok(v),
                Err(err) => {
                    // Classify via the typed Trap in the error chain — the
                    // top-level Display is just the backtrace header.
                    match err.downcast_ref::<wasmtime::Trap>() {
                        Some(wasmtime::Trap::OutOfFuel) => Err(BudgetKill::FuelExhausted),
                        Some(wasmtime::Trap::Interrupt) => Err(BudgetKill::EpochDeadline),
                        _ => {
                            // chain text fallback for version drift
                            let chain = format!("{err:?}");
                            if chain.contains("fuel") {
                                Err(BudgetKill::FuelExhausted)
                            } else if chain.contains("epoch") || chain.contains("interrupt") {
                                Err(BudgetKill::EpochDeadline)
                            } else {
                                return Err(EngineError::Wasmtime(chain));
                            }
                        }
                    }
                }
            })
        })();

        stop.store(true, std::sync::atomic::Ordering::Relaxed);
        let _ = ticker.join();
        result
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    const QUICK: &str = r#"(module (func (export "f") (result i32) i32.const 7))"#;
    /// Infinite loop — only budgets can stop it.
    const SPIN: &str = r#"(module (func (export "f") (result i32) (loop br 0) i32.const 0))"#;

    #[test]
    fn well_behaved_guest_completes_under_budget() {
        let eng = PluginEngine::new().unwrap();
        let r = eng
            .run_with_budgets(
                QUICK,
                "f",
                100_000,
                Duration::from_secs(2),
                Duration::from_millis(10),
            )
            .unwrap();
        assert_eq!(r, Ok(7));
    }

    #[test]
    fn fuel_exhaustion_kills_deterministically() {
        let eng = PluginEngine::new().unwrap();
        // tiny fuel, generous wall: fuel must be the killer
        let r = eng
            .run_with_budgets(
                SPIN,
                "f",
                10_000,
                Duration::from_secs(30),
                Duration::from_millis(50),
            )
            .unwrap();
        assert_eq!(r, Err(BudgetKill::FuelExhausted));
    }

    #[test]
    fn epoch_deadline_kills_wall_clock_runaway() {
        let eng = PluginEngine::new().unwrap();
        // huge fuel, tight wall: epoch must be the killer
        let r = eng
            .run_with_budgets(
                SPIN,
                "f",
                u64::MAX / 2,
                Duration::from_millis(100),
                Duration::from_millis(10),
            )
            .unwrap();
        assert_eq!(r, Err(BudgetKill::EpochDeadline));
    }
}
