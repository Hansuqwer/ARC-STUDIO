//! macOS NSAccessibility bridge for the gpui shell (G5).
//!
//! Translates the ARC-owned `arc_ui::a11y::ShellA11yTree` into a flat list of
//! `NSAccessibilityElement` children attached to gpui's content NSView. The
//! accessibility *truth* stays in `arc-ui` (framework-free); this file is the
//! ~platform bridge only — the single thing that changes if the framework
//! swaps to the floem escape.
//!
//! gpui 0.2.2 exposes the content view via `Window: HasWindowHandle`
//! (AppKitWindowHandle → NSView ptr). We do not subclass or patch gpui; we
//! attach sibling accessibility elements to the existing view.

#![cfg(all(feature = "framework-gpui", target_os = "macos"))]

use arc_ui::a11y::{A11yRole, ShellA11yTree};
use arc_ui::kit::Window;
use objc2::rc::Retained;
use objc2::runtime::AnyObject;
use objc2_app_kit::{
    NSAccessibilityElement, NSAccessibilityGroupRole, NSAccessibilityListRole,
    NSAccessibilityRole, NSAccessibilityRowRole, NSAccessibilityStaticTextRole,
    NSAccessibilityTextFieldRole,
};
use objc2_foundation::{NSArray, NSRect, NSString};
use raw_window_handle::{HasWindowHandle, RawWindowHandle};

fn ns_role(role: A11yRole) -> &'static NSAccessibilityRole {
    // SAFETY: these are framework static globals, valid for the process.
    unsafe {
        match role {
            A11yRole::Group | A11yRole::Dialog => NSAccessibilityGroupRole,
            A11yRole::TextField => NSAccessibilityTextFieldRole,
            A11yRole::List => NSAccessibilityListRole,
            A11yRole::Row => NSAccessibilityRowRole,
            A11yRole::StaticText => NSAccessibilityStaticTextRole,
        }
    }
}

/// Attach the ARC accessibility tree to the gpui window's content NSView.
///
/// Call from `render()` each frame (cheap: rebuilds a flat element list from
/// the current tree). VoiceOver reads the attached children; the Metal surface
/// is no longer one opaque element (the G5 step-2 failure mode).
///
/// Returns the number of accessibility elements attached (for evidence/log).
pub fn attach_a11y_tree(window: &Window, tree: &ShellA11yTree) -> usize {
    let view_ptr = match HasWindowHandle::window_handle(window).map(|h| h.as_raw()) {
        Ok(RawWindowHandle::AppKit(handle)) => handle.ns_view.as_ptr(),
        _ => return 0,
    };

    // SAFETY: ns_view points at the live NSView gpui owns for this window; we
    // only call AppKit accessibility setters on the main thread (render is
    // main-thread in gpui). We do not retain it beyond this call.
    let view: &AnyObject = unsafe { &*(view_ptr as *const AnyObject) };

    // Window frame in screen coordinates (bottom-left origin) — VoiceOver
    // culls zero-frame elements, so every child needs a real on-screen rect.
    // SAFETY: -[NSView window] then -[NSWindow frame]; both main-thread.
    let win_frame: NSRect = unsafe {
        let window_obj: *mut AnyObject = objc2::msg_send![view, window];
        if window_obj.is_null() {
            NSRect::default()
        } else {
            objc2::msg_send![window_obj, frame]
        }
    };

    let flat = tree.flatten();
    let n = flat.len().max(1) as f64;
    // Stack elements top-to-bottom inside the window frame. AppKit screen
    // coords are bottom-left origin, so row 0 (tree root) sits at the top.
    let row_h = (win_frame.size.height / n).max(1.0);
    let mut elements: Vec<Retained<AnyObject>> = Vec::with_capacity(flat.len());

    for (i, (role, label, value, _focused)) in flat.iter().enumerate() {
        let label_with_value = match value {
            Some(v) if !v.is_empty() => format!("{label}: {v}"),
            _ => label.clone(),
        };
        let ns_label = NSString::from_str(&label_with_value);
        let top_y = win_frame.origin.y + win_frame.size.height - (i as f64 + 1.0) * row_h;
        let frame = NSRect::new(
            objc2_foundation::NSPoint::new(win_frame.origin.x, top_y),
            objc2_foundation::NSSize::new(win_frame.size.width.max(1.0), row_h),
        );
        // SAFETY: role is a valid framework constant; parent=None makes these
        // children of the view we set them on below; label is a valid NSString.
        let element = unsafe {
            NSAccessibilityElement::accessibilityElementWithRole_frame_label_parent(
                ns_role(*role),
                frame,
                Some(&ns_label),
                None,
            )
        };
        elements.push(element);
    }

    let array = NSArray::from_retained_slice(&elements);

    // SAFETY: NSView conforms to NSAccessibility. Main-thread call.
    // Container view must NOT be a leaf element (false) so its children are
    // navigable; we then publish the children array and the window title.
    unsafe {
        let _: () = objc2::msg_send![view, setAccessibilityElement: false];
        let _: () = objc2::msg_send![view, setAccessibilityChildren: &*array];
        let title = NSString::from_str(&tree.window_title);
        let _: () = objc2::msg_send![view, setAccessibilityLabel: &*title];
    }

    elements.len()
}

#[cfg(test)]
mod tests {
    use super::*;
    use arc_ui::a11y::A11ySnapshot;

    #[test]
    fn role_mapping_is_total() {
        // Every ARC role maps to a non-null NS role constant.
        for role in [
            A11yRole::Group,
            A11yRole::Dialog,
            A11yRole::TextField,
            A11yRole::List,
            A11yRole::Row,
            A11yRole::StaticText,
        ] {
            let _ = ns_role(role); // must not panic / null-deref
        }
    }

    #[test]
    fn tree_flattens_for_bridge() {
        let regions = [
            ("workspace", "Workspace tree"),
            ("editor", "Editor"),
            ("dock", "ARC dock"),
            ("status", "Status rail"),
        ];
        let snap = A11ySnapshot {
            focused_region_id: "workspace",
            regions: &regions,
            palette_open: false,
            palette_query: "",
            palette_rows: &[],
            palette_selected: 0,
            typebox_text: "",
            status_rail: "● daemon healthy | trust: trusted",
        };
        let tree = ShellA11yTree::build(&snap);
        // root + 4 regions + status rail + typebox = 7 elements
        assert_eq!(tree.flatten().len(), 7);
    }
}
