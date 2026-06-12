//! FocusRing — deterministic focus traversal across labeled landmark regions
//! (wireframe §6.1: every region is a labeled landmark; F6-style cycling).
//! Sprint-2 exit gate: deterministic focus traversal — proven here as a model,
//! re-proven against the real framework in Sprint 3 (G5).

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Region {
    pub id: &'static str,
    /// Accessible name announced when the region receives focus.
    pub label: &'static str,
}

#[derive(Debug, Default)]
pub struct FocusRing {
    regions: Vec<Region>,
    current: usize,
}

impl FocusRing {
    pub fn new(regions: Vec<Region>) -> Self {
        Self {
            regions,
            current: 0,
        }
    }

    pub fn current(&self) -> Option<&Region> {
        self.regions.get(self.current)
    }

    /// F6: cycle forward; wraps. Returns the newly focused region for the
    /// renderer to announce.
    pub fn focus_next(&mut self) -> Option<&Region> {
        if self.regions.is_empty() {
            return None;
        }
        self.current = (self.current + 1) % self.regions.len();
        self.current()
    }

    /// Shift+F6: cycle backward; wraps.
    pub fn focus_prev(&mut self) -> Option<&Region> {
        if self.regions.is_empty() {
            return None;
        }
        self.current = (self.current + self.regions.len() - 1) % self.regions.len();
        self.current()
    }

    /// Jump to a region by id (e.g. palette "go to panel" command).
    pub fn focus(&mut self, id: &str) -> Option<&Region> {
        let idx = self.regions.iter().position(|r| r.id == id)?;
        self.current = idx;
        self.current()
    }

    /// (id, label) pairs in focus order — for the accessibility bridge to
    /// expose each region as a labeled landmark.
    pub fn regions_for_a11y(&self) -> Vec<(&str, &str)> {
        self.regions.iter().map(|r| (r.id, r.label)).collect()
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    fn ring() -> FocusRing {
        FocusRing::new(vec![
            Region {
                id: "workspace",
                label: "Workspace tree",
            },
            Region {
                id: "editor",
                label: "Editor",
            },
            Region {
                id: "dock",
                label: "ARC dock",
            },
            Region {
                id: "status",
                label: "Status rail",
            },
        ])
    }

    #[test]
    fn f6_cycles_deterministically_and_wraps() {
        let mut r = ring();
        let order: Vec<&str> = (0..5).map(|_| r.focus_next().unwrap().id).collect();
        assert_eq!(
            order,
            vec!["editor", "dock", "status", "workspace", "editor"]
        );
    }

    #[test]
    fn shift_f6_reverses() {
        let mut r = ring();
        assert_eq!(r.focus_prev().unwrap().id, "status"); // wrap backward from first
        assert_eq!(r.focus_prev().unwrap().id, "dock");
    }

    #[test]
    fn jump_by_id() {
        let mut r = ring();
        assert_eq!(r.focus("dock").unwrap().label, "ARC dock");
        assert!(r.focus("nonexistent").is_none());
        assert_eq!(r.current().unwrap().id, "dock", "failed jump keeps focus");
    }
}
